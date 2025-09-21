#!/usr/bin/env python3
# plutuscope.py
"""
Plutuscope - validator narration, simulation, and trace explorer
Usage:
  python plutuscope_report.py --aiken <file> [--simulate] [--tests <log>]
  python plutuscope_report.py --scan <dir> [--no-aiken] [--instrument] [--verbose]
"""
import os
import re
import sys
import shutil
import subprocess
import json
import tempfile
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path
from datetime import datetime, timezone
import argparse

from rich import print as rprint
from rich.table import Table
from rich.console import Console
from rich.tree import Tree
from rich.text import Text
from rich.prompt import Prompt

console = Console()
# project-wide cache for parsed tests (populated once per run)
_project_tests_cache: Optional[List[Dict[str, Any]]] = None
_project_tests_cache_root: Optional[Path] = None

# ======================================================================
# === TRACE + SCAN MODE (from plutuscope_cli.py) - improved
# ======================================================================

TRACE_RE = re.compile(r'^\s*\[TRACE\]\s*(.*)$', re.I)
ENTER_RE = re.compile(r'Entering function\s+([A-Za-z_]\w*)', re.I)
RETURN_RE = re.compile(r'Returning\s+(.*)', re.I)
CHECK_RE = re.compile(r'(?:check|matching)\s+(.*?)(?:\s*[-–—>]{1,2}\s*(true|false))?$', re.I)
LINE_TAG_RE = re.compile(r'\bL(\d+)\b')
TEST_LINE_RE = re.compile(r'(?:test[:\s-]+)?([A-Za-z0-9_\-./]+)\s*(PASS|FAIL|OK|FAILED|ERROR)?', re.I)

@dataclass
class Node:
    title: str
    status: Optional[bool] = None
    children: List["Node"] = field(default_factory=list)
    src_loc: Optional[Tuple[Optional[str], Optional[int]]] = None

def find_ak_files(root: str) -> List[Path]:
    p = Path(root)
    out = []
    for fp in p.rglob("*.ak"):
        if fp.is_file():
            out.append(fp.resolve())
    return sorted(out)

def find_project_root(start: Path) -> Optional[Path]:
    cur = start if start.is_dir() else start.parent
    for parent in [cur] + list(cur.parents):
        if (parent / "aiken.toml").exists():
            return parent
    return None

def run_aiken_on_file(file_path: Path, project_dir: Optional[Path] = None, timeout: int = 30, verbose: bool=False) -> Tuple[int, str, str]:
    """
    Run `aiken check` on the file or project_dir. Capture stdout to a temp file to
    avoid lost output and return (rc, stdout_text, stderr_text).
    """
    if shutil.which("aiken") is None:
        return (127, "", "aiken not found on PATH")

    # prefer running from project root (if available), else parent
    cwd = str(project_dir or find_project_root(file_path) or file_path.parent)
    tmp_out = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".out", mode="w", encoding="utf8") as tmp:
            tmp_out = tmp.name

        # run aiken check pointed at the project directory (not the single file)
        try:
            with open(tmp_out, "w", encoding="utf8") as out:
                proc = subprocess.run(
                    ["aiken", "check", str(cwd)],
                    stdout=out,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=str(cwd),
                    timeout=timeout,
                )
            rc = proc.returncode
            stderr = proc.stderr or ""
        except subprocess.TimeoutExpired:
            return (124, "", "aiken check timed out")
        except Exception as e:
            return (1, "", f"aiken error: {e}")

        stdout_text = ""
        try:
            stdout_text = Path(tmp_out).read_text(encoding="utf8")
        except Exception:
            stdout_text = ""

        if verbose:
            console.log(f"[dim]aiken rc={rc} stdout_preview={stdout_text[:200]!r} stderr_preview={stderr[:200]!r}")

        return (rc, stdout_text, stderr)
    finally:
        if tmp_out:
            try:
                os.unlink(tmp_out)
            except Exception:
                pass

TRACE_CALL_RE = re.compile(r'\btrace\b\s*(?:@?"([^"]+)"|\'([^\']+)\')?', re.I)
FN_DEF_RE = re.compile(r'^\s*fn\s+([A-Za-z_]\w*)\s*\(', re.I)

def mock_traces_from_file(file_path: Path) -> str:
    """
    Create a helpful mock trace output by scanning the file for function defs and trace calls.
    """
    try:
        lines = file_path.read_text(encoding="utf8", errors="ignore").splitlines()
    except Exception:
        lines = []
    out_lines = []
    for i, L in enumerate(lines, start=1):
        m = FN_DEF_RE.match(L)
        if m:
            fname = m.group(1)
            out_lines.append(f"[TRACE] Entering function {fname} L{i}")
            snippet = "\n".join(lines[i:min(i+30, len(lines))])
            for tm in TRACE_CALL_RE.finditer(snippet):
                lbl = tm.group(1) or tm.group(2) or "trace"
                out_lines.append(f"[TRACE] {lbl} L{i}")
            out_lines.append(f"[TRACE] check sample_check -> true L{i}")
            out_lines.append(f"[TRACE] Returning <mock-value> L{i}")
    if not out_lines:
        out_lines = ["[TRACE] No functions found; file scanned (mock)"]
    return "\n".join(out_lines)

def parse_trace(log_text: str, file_hint: Optional[Path] = None) -> Node:
    """
    Parse trace lines into a nested Node tree (enter/return/check/msg).
    """
    root = Node("execution")
    stack: List[Node] = [root]
    for raw in log_text.splitlines():
        m = TRACE_RE.match(raw)
        if not m:
            # also allow plain lines (no [TRACE]) to be processed (fallback)
            msg = raw.strip()
            if not msg:
                continue
        else:
            msg = m.group(1).strip()

        line_num = None
        lm = LINE_TAG_RE.search(msg)
        if lm:
            try:
                line_num = int(lm.group(1))
            except:
                line_num = None

        me = ENTER_RE.search(msg)
        if me:
            name = me.group(1)
            src = (str(file_hint) if file_hint else None, line_num)
            node = Node(f"enter {name}", src_loc=src if (file_hint or line_num) else None)
            stack[-1].children.append(node)
            stack.append(node)
            continue

        mr = RETURN_RE.search(msg)
        if mr:
            val = mr.group(1).strip()
            src = (str(file_hint) if file_hint else None, line_num)
            node = Node(f"return {val}", src_loc=src if (file_hint or line_num) else None)
            stack[-1].children.append(node)
            if len(stack) > 1:
                stack.pop()
            continue

        mc = CHECK_RE.search(msg)
        if mc:
            expr = mc.group(1).strip()
            res = mc.group(2)
            status = None
            if res:
                status = res.lower() == "true"
            src = (str(file_hint) if file_hint else None, line_num)
            node = Node(expr, status=status, src_loc=src if (file_hint or line_num) else None)
            stack[-1].children.append(node)
            continue

        # test boundary detection (try to group traces under test names later)
        mt = TEST_LINE_RE.search(msg)
        if mt and (mt.group(2) is not None or msg.lower().startswith("test")):
            # treat as a top-level note
            name = mt.group(1)
            node = Node(f"test: {name}")
            stack[-1].children.append(node)
            continue

        src = (str(file_hint) if file_hint else None, line_num)
        node = Node(msg, src_loc=src if (file_hint or line_num) else None)
        stack[-1].children.append(node)

    return root

def render_node_tree(node: Node, parent: Optional[Tree] = None) -> Tree:
    lab = node.title
    if node.status is True:
        if not re.search(r'\btrue\b', lab, re.I):
            lab = f"{lab} -> true"
    elif node.status is False:
        if not re.search(r'\bfalse\b', lab, re.I):
            lab = f"{lab} -> false"

    if node.src_loc:
        fp, ln = node.src_loc
        if ln is not None:
            if fp:
                lab = f"{lab}  | {os.path.basename(fp)}:{ln}"
            else:
                lab = f"{lab}  | L{ln}"

    text_obj = Text(lab)
    for m in re.finditer(r'\btrue\b', lab, flags=re.I):
        text_obj.stylize("green", *m.span())
    for m in re.finditer(r'\bfalse\b', lab, flags=re.I):
        text_obj.stylize("red", *m.span())

    src_idx = lab.rfind("  | ")
    if src_idx != -1:
        text_obj.stylize("dim", src_idx, len(lab))

    if node.status is True:
        text_obj = Text("✅ ") + text_obj
    elif node.status is False:
        text_obj = Text("❌ ") + text_obj

    if parent is None:
        tree = Tree(text_obj)
    else:
        tree = parent.add(text_obj)

    for c in node.children:
        render_node_tree(c, tree)
    return tree

# ======================================================================
# === Aiken test/result helpers: robust capture + fallbacks
# ======================================================================

def _read_test_fallbacks(project_dir: Path, verbose: bool=False) -> Optional[dict]:
    """
    Look for fallback files that commonly contain test results:
      - project_dir/plutus.json
      - project_dir/tests.log
    Returns a dict with "tests": [...]
    """
    # 1) plutus.json
    pj = project_dir / "plutus.json"
    if pj.exists():
        try:
            with pj.open("r", encoding="utf8") as f:
                parsed = json.load(f)
                # If parsed is already shaped with "tests" key, return directly
                if isinstance(parsed, dict) and "tests" in parsed:
                    return parsed
                # else wrap if it's a list
                if isinstance(parsed, list):
                    return {"tests": parsed}
                return {"plutus": parsed}
        except Exception as e:
            if verbose:
                console.log(f"⚠️ Could not parse {pj} as JSON: {e}")

    # 2) tests.log
    tl = project_dir / "tests.log"
    if tl.exists():
        try:
            text = tl.read_text(encoding="utf8").strip()
            if not text:
                return None
            # try JSON first
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict) and "tests" in parsed:
                    return parsed
                if isinstance(parsed, list):
                    return {"tests": parsed}
            except json.JSONDecodeError:
                # Not JSON: attempt heuristic parse
                tests = []
                for line in text.splitlines():
                    s = line.strip()
                    if not s:
                        continue
                    lower = s.lower()
                    status = None
                    if any(tok in lower for tok in ("pass", "ok", "✓")):
                        status = "ok"
                    elif any(tok in lower for tok in ("fail", "failed", "✗", "x")):
                        status = "fail"
                    # attempt to get a name (strip status tokens)
                    name = re.sub(r'[:\-\s]*(pass|ok|failed|fail|✓|✗)$', '', s, flags=re.I).strip()
                    if not name:
                        name = s
                    tests.append({"name": name, "status": status or "unknown"})
                if tests:
                    return {"tests": tests}
        except Exception as e:
            if verbose:
                console.log(f"⚠️ Could not read {tl}: {e}")

    return None

def _extract_trace_lines_from_text(text: str) -> List[str]:
    lines = []
    for ln in text.splitlines():
        if '[TRACE]' in ln or 'trace(' in ln or 'Entering function' in ln or 'Returning' in ln:
            lines.append(ln.strip())
    return lines

def run_aiken_and_collect(project_dir: Path, instrument: bool=False, verbose: bool=False) -> dict:
    """
    Run aiken (if present) against project_dir, collect tests and trace lines.
    If instrument=True, run against an instrumented temp copy (which will be cleaned).
    Returns a dict that may contain:
      - tests: list of {name, status}
      - raw_trace_lines: [...]
      - raw_stdout / raw_stderr (if verbose)
      - plutus / plutus.json data (if present)
    """
    tmp_project = None
    used_dir = project_dir
    if instrument:
        tmp_project = _instrument_project_for_traces(project_dir, verbose=verbose)
        if tmp_project:
            used_dir = tmp_project
        else:
            console.log("[yellow]Instrumentation failed — continuing against original project.")

    results: Dict[str, Any] = {}
    try:
        if shutil.which("aiken"):
            rc, stdout_text, stderr_text = run_aiken_on_file(project_dir, project_dir, verbose=verbose)
            if verbose:
                results["_raw_aiken_stdout"] = stdout_text[:5000]
                results["_raw_aiken_stderr"] = stderr_text[:2000]
            # try parse JSON from stdout
            parsed_json = None
            try:
                parsed_json = json.loads(stdout_text.strip()) if stdout_text.strip() else None
            except Exception:
                parsed_json = None

            # collect trace-like lines from stdout
            trace_lines = _extract_trace_lines_from_text(stdout_text)
            # also look into stderr for traces (some tools print to stderr)
            trace_lines += _extract_trace_lines_from_text(stderr_text)

            # if we have a parsed_json that includes tests -> return that
            if isinstance(parsed_json, dict) and "tests" in parsed_json:
                results.update(parsed_json)
                if trace_lines:
                    results.setdefault("raw_trace_lines", []).extend(trace_lines)
                return results

            # else, try reading fallback files in project dir and merge
            fallback = _read_test_fallbacks(used_dir, verbose=verbose)
            if fallback:
                results.update(fallback)
            if trace_lines:
                results.setdefault("raw_trace_lines", []).extend(trace_lines)

            # if nothing found yet, include stdout as raw text
            if not results:
                if stdout_text.strip():
                    results["_raw_stdout"] = stdout_text
                if stderr_text.strip():
                    results["_raw_stderr"] = stderr_text

            return results
        else:
            # aiken not present: use fallbacks only
            fallback = _read_test_fallbacks(used_dir, verbose=verbose)
            if fallback:
                results.update(fallback)
            # also attempt to parse tests.log/traces as raw lines
            tl = used_dir / "tests.log"
            if tl.exists():
                txt = tl.read_text(encoding="utf8", errors="ignore")
                results.setdefault("raw_trace_text", txt)
                lines = _extract_trace_lines_from_text(txt)
                if lines:
                    results.setdefault("raw_trace_lines", []).extend(lines)
            pj = used_dir / "plutus.json"
            if pj.exists():
                results.setdefault("plutus.json", pj.read_text(encoding="utf8", errors="ignore")[:5000])
            return results
    finally:
        if tmp_project:
            try:
                shutil.rmtree(tmp_project)
            except Exception:
                pass

# ======================================================================
# === Instrumentation helper (temporary copy + trace insertion)
# ======================================================================

def _instrument_project_for_traces(project_dir: Path, verbose: bool=False) -> Optional[Path]:
    """
    Copy project to temp dir and insert trace("enter ...") / trace("exit ...")
    at the beginning/end of functions in .ak files.
    Return path to temp project or None on failure.
    """
    try:
        tmp_root = Path(tempfile.mkdtemp(prefix="aiken_instrument_"))
        shutil.copytree(project_dir, tmp_root, dirs_exist_ok=True)
        for ak in tmp_root.rglob("*.ak"):
            try:
                text = ak.read_text(encoding="utf8", errors="ignore")
            except Exception:
                continue
            new_parts = []
            idx = 0
            FN_RE = re.compile(r'(fn\s+([A-Za-z_]\w*)\s*\([^)]*\)\s*{)', re.I | re.M)
            for m in FN_RE.finditer(text):
                start, brace_pos = m.start(1), m.end(1)-1
                new_parts.append(text[idx:start])
                header = text[start:brace_pos+1]
                new_parts.append(header)
                # extract balanced block
                try:
                    body, end_idx = _extract_balanced_block(text, brace_pos)
                except Exception:
                    # cannot parse: append rest and break
                    new_parts.append(text[brace_pos+1:])
                    idx = len(text)
                    break
                fname = m.group(2)
                # insert entry and exit traces (best-effort)
                instrumented = '\ntrace("enter {}");\n'.format(fname) + body + '\ntrace("exit {}");\n'.format(fname)
                new_parts.append(instrumented)
                idx = end_idx + 1
            if idx < len(text):
                new_parts.append(text[idx:])
            new_text = ''.join(new_parts)
            if new_text != text:
                ak.write_text(new_text, encoding="utf8")
        return tmp_root
    except Exception as e:
        if verbose:
            console.log(f"[red]instrumentation error: {e}")
        return None
    
def _synthesize_traces_from_instrumented(tmp_project: Path) -> List[str]:
    """
    Scan instrumented .ak files for trace("...") and trace(@"...") inserts and produce
    [TRACE] lines that mimic aiken output. Returns list of trace lines.
    """
    trace_lines = []
    TA = re.compile(r'trace\s*\(\s*@?"([^"]+)"\s*\)\s*;?', re.I)
    for ak in tmp_project.rglob("*.ak"):
        try:
            txt = ak.read_text(encoding="utf8", errors="ignore")
        except Exception:
            continue
        lines = txt.splitlines()
        for i, L in enumerate(lines, start=1):
            for m in TA.finditer(L):
                lbl = m.group(1) or "trace"
                trace_lines.append(f"[TRACE] {lbl} L{i}  | {ak.name}")
    return trace_lines


def _extract_balanced_block(text: str, open_brace_index: int) -> Tuple[str, int]:
    if open_brace_index < 0 or open_brace_index >= len(text) or text[open_brace_index] != '{':
        raise ValueError("open_brace_index must point to '{'")
    depth = 0
    i = open_brace_index
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return text[open_brace_index + 1:i], i
        i += 1
    raise ValueError("Unbalanced braces: no matching '}' found.")

def _extract_balanced_paren(text: str, open_paren_index: int) -> Tuple[str, int]:
    if open_paren_index < 0 or open_paren_index >= len(text) or text[open_paren_index] != '(':
        raise ValueError("open_paren_index must point to '('")
    depth = 0
    i = open_paren_index
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth == 0:
                return text[open_paren_index + 1:i], i
        i += 1
    raise ValueError("Unbalanced parens: no matching ')' found.")

# --- Test parsing & mapping helpers ---
TEST_DECL_RE = re.compile(
    r'(?:\s*#\[[^\]]+\]\s*)*\btest\s+([A-Za-z0-9_\-]+)\s*\(([^)]*)\)\s*(fail)?\s*{', re.I)
TEST_CALL_RE = re.compile(r'(!)?\s*([A-Za-z_]\w*)\.([A-Za-z_]\w*)\s*\(', re.I)  # captures optional '!' negation, validator, method
TRACE_INLINE_RE = re.compile(r'trace\s*@?"([^"]+)"', re.I)  # matches trace @"..." or trace "..." or trace@"..."

def parse_tests_in_text(text: str) -> List[Dict[str, Any]]:
    """
    Parse tests in a file's text and return list of dicts:
      { name, fail_declared (bool), body (str), calls: [ {negated(bool), validator, method, line_no, snippet}, ...],
        traces: [ <trace strings> ]
      }
    """
    tests = []
    # iterate through each test declaration and extract balanced body
    for m in TEST_DECL_RE.finditer(text):
        name = m.group(1)
        fail_declared = bool(m.group(3))
        open_idx = m.end() - 1  # index of '{'
        try:
            body, close_idx = _extract_balanced_block(text, open_idx)
        except ValueError:
            body = ""
        # find calls within body
        calls = []
        # compute approximate starting line number for better diagnostics
        start_line = text.count("\n", 0, m.start()) + 1
        for cm in TEST_CALL_RE.finditer(body):
            neg = bool(cm.group(1))
            validator = cm.group(2)
            method = cm.group(3)
            call_pos = cm.start()
            line_no = start_line + body.count("\n", 0, call_pos)
            snippet = body[max(0, call_pos-30): call_pos+120].replace("\n", " ")
            calls.append({"negated": neg, "validator": validator, "method": method, "line": line_no, "snippet": snippet})
        # collect inline trace strings in test body
        traces = [g for g in TRACE_INLINE_RE.findall(body)]
        # also collect any explicit [TRACE] lines (if test log text was pasted instead of source)
        tests.append({"name": name, "fail_declared": fail_declared, "body": body, "calls": calls, "traces": traces})
    return tests

# --- Project-wide function lookup (re-uses existing find_project_root) ---
def _find_function_project_wide(project_root: Path, fname: str, exclude_path: Optional[Path]=None) -> List[Tuple[Path,int,str]]:
    matches = []
    for ak in project_root.rglob("*.ak"):
        if exclude_path and ak.resolve() == exclude_path.resolve():
            continue
        try:
            txt = ak.read_text(encoding="utf8", errors="ignore")
        except Exception:
            continue
        # simple search for 'fn fname' pattern
        m = re.search(r'\bfn\s+' + re.escape(fname) + r'\b', txt)
        if m:
            idx = m.start()
            line_no = txt.count("\n", 0, idx) + 1
            snippet = txt[max(0, idx-80): idx+200].replace("\n", " ")
            matches.append((ak, line_no, snippet))
    return matches

# ======================================================================
# === Scan / analyze flow (main integration)
# ======================================================================

def analyze_files(paths: List[Path], prefer_aiken: bool = True, instrument: bool=False, verbose: bool=False):
    """
    Scan the given paths. Expensive operations (aiken runs, instrumentation) are
    cached per project directory so we don't repeat them for every file.
    """
    results = []
    # cache per project dir (and instrument/prefer_aiken flags) -> collected dict
    project_cache: Dict[Tuple[str, bool, bool], dict] = {}

    for p in paths:
        console.rule(f"[bold blue]Scanning {p}")
        project_dir = find_project_root(p) or p.parent

        cache_key = (str(project_dir.resolve()), bool(prefer_aiken), bool(instrument))
        collected = None
        note = "mock (aiken not present)"
        raw_text = ""

        # Try to reuse cached collection for this project
        if cache_key in project_cache:
            collected = project_cache[cache_key]
        else:
            # perform the expensive collection once per project
            if prefer_aiken and shutil.which("aiken"):
                collected = run_aiken_and_collect(project_dir, instrument=instrument, verbose=verbose)
            else:
                # Aiken not present (or disabled): still try to instrument + synthesize traces if requested
                if instrument:
                    tmp_project = _instrument_project_for_traces(project_dir, verbose=verbose)
                    if tmp_project:
                        # synthesize trace lines from instrumented files
                        synthesized = _synthesize_traces_from_instrumented(Path(tmp_project))
                        collected = {"raw_trace_lines": synthesized} if synthesized else {}
                        try:
                            shutil.rmtree(tmp_project)
                        except Exception:
                            pass
                    else:
                        # instrumentation failed — fallback to reading fallbacks
                        collected = run_aiken_and_collect(project_dir, instrument=False, verbose=verbose)
                else:
                    collected = run_aiken_and_collect(project_dir, instrument=False, verbose=verbose)

            project_cache[cache_key] = collected or {}

        # derive a displayable raw_text and note from collected results
        if collected.get("raw_trace_lines"):
            raw_lines = collected["raw_trace_lines"]
            raw_text = "\n".join(raw_lines)
            note = "aiken (traces)" if shutil.which("aiken") else "instrumented-mock"
        elif collected.get("tests"):
            tests = collected["tests"]
            raw_text = ""
            for t in tests:
                raw_text += f"[TRACE] Test {t.get('name','<unnamed>')} {t.get('status','')}\n"
            if collected.get("raw_trace_lines"):
                raw_text += "\n".join(collected["raw_trace_lines"])
            note = "aiken (tests)"
        elif collected.get("_raw_aiken_stdout"):
            raw = collected["_raw_aiken_stdout"]
            extracted = _extract_trace_lines_from_text(raw)
            if extracted:
                raw_text = "\n".join(extracted)
                note = "aiken (raw traces)"
            else:
                raw_text = raw[:4000]
                note = "aiken (raw)"
        else:
            # fallback to mock traces from source file (cheap local parse)
            raw_text = mock_traces_from_file(p)
            note = "mock (aiken produced no test/traces)"

        tree = parse_trace(raw_text, file_hint=p)
        results.append({"path": p, "tree": tree, "raw": raw_text, "note": note})

    return results



def print_summary_table(results):
    t = Table(title="Plutuscope - .ak file scan")
    t.add_column("Index", justify="right")
    t.add_column("File", justify="left")
    t.add_column("Traces", justify="right")
    t.add_column("Source", justify="left")
    for i, r in enumerate(results, start=1):
        count = r["raw"].count("[TRACE]")
        try:
            rel = os.path.relpath(str(r["path"]), Path.cwd())
        except Exception:
            rel = str(r["path"])
        t.add_row(str(i), rel, str(count), r["note"])
    console.print(t)

def interactive_browser(results):
    while True:
        print_summary_table(results)
        choice = Prompt.ask("Enter an index to view tree, 'r' to rerun, 'q' to quit", default="q")
        cl = choice.strip().lower()
        if cl in ("q", "quit", "exit"):
            return None
        if cl == "r":
            return "rerun"
        try:
            idx = int(choice) - 1
        except Exception:
            rprint("[red]Invalid input (enter a number, r, or q).")
            continue
        if not (0 <= idx < len(results)):
            rprint("[red]Invalid index")
            continue

        r = results[idx]
        console.rule(f"[green]Traces for {r['path'].name}")
        tree = render_node_tree(r["tree"])
        console.print(tree)

        if Prompt.ask("Show raw trace text? ", choices=["y", "n"], default="n") == "y":
            for line in r["raw"].splitlines():
                colored = re.sub(r'\btrue\b', '[green]true[/]', line)
                colored = re.sub(r'\bfalse\b', '[red]false[/]', colored)
                console.print(colored)

# ======================================================================
# === NARRATION + SIMULATION MODE (kept simple)
# ======================================================================

def _find_functions_in_text(text: str) -> List[Tuple[str, str, str]]:
    """
    More tolerant finder for `fn name(args) [-> Type] { body }`.
    It allows a larger window between ')' and '{' (up to 2000 chars),
    and is permissive about whitespace/comments/return annotations in-between.
    """
    if text.startswith("\ufeff"):
        text = text.lstrip("\ufeff")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    out: List[Tuple[str, str, str]] = []
    i = 0
    n = len(text)
    MAX_BETWEEN = 2000  # larger window

    while True:
        m = re.search(r'\bfn\s+([A-Za-z_]\w*)', text[i:], re.M)
        if not m:
            break
        fn_name = m.group(1)
        fn_pos = i + m.start()

        paren_idx = text.find('(', fn_pos)
        if paren_idx == -1:
            i = fn_pos + 2
            continue

        try:
            args_text, paren_close_idx = _extract_balanced_paren(text, paren_idx)
        except ValueError:
            i = fn_pos + 2
            continue

        # search for '{' within the larger window
        search_start = paren_close_idx + 1
        search_end = min(n, search_start + MAX_BETWEEN)
        brace_idx = text.find('{', search_start, search_end)
        if brace_idx == -1:
            i = fn_pos + 2
            continue

        between = text[paren_close_idx + 1:brace_idx]

        # be permissive: accept whitespace, arrow annotation, comments, or reasonably sized between
        if not re.fullmatch(r'[\s]*|[\s]*->[\sA-Za-z0-9_\-,.<>\[\]\{\}\|:\s/*]+', between):
            # If between is long but contains valid tokens, allow it; otherwise skip
            if len(between) > 800:
                i = fn_pos + 2
                continue

        try:
            body_text, brace_close_idx = _extract_balanced_block(text, brace_idx)
        except ValueError:
            i = fn_pos + 2
            continue

        out.append((fn_name, args_text.strip(), body_text))
        i = brace_close_idx + 1

    return out




# ----------------------------
# Small safe helper for printing relative paths (use in pretty_print_validator)
# ----------------------------
def _relpath_or_str(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except Exception:
        return str(path)
    
# --- detect methods inside a validator block (e.g. `spend(...){...}`, `mint(...) { ... }`, `else(_) { ... }`) ---
def _find_methods_in_validator_body(vbody: str) -> List[Tuple[str, str, str]]:
    """
    Return list of (method_name, args_text, body_text) found inside a validator body.
    Robust to multiline args and nested braces inside method body.
    """
    out: List[Tuple[str, str, str]] = []
    i = 0
    n = len(vbody)
    while True:
        # find next token that looks like a method name followed by '('
        m = re.search(r'\b([A-Za-z_]\w*)\s*\(', vbody[i:])
        if not m:
            break
        name = m.group(1)
        name_pos = i + m.start()
        paren_idx = vbody.find('(', name_pos)
        if paren_idx == -1:
            i = name_pos + 1
            continue
        # extract balanced paren contents
        try:
            args_text, paren_close = _extract_balanced_paren(vbody, paren_idx)
        except ValueError:
            i = name_pos + 1
            continue
        # skip whitespace/comments until next non-space char, expecting '{'
        k = paren_close + 1
        while k < n and vbody[k].isspace():
            k += 1
        if k >= n or vbody[k] != '{':
            # not a method with body (maybe a call), skip this occurrence
            i = name_pos + 1
            continue
        # extract balanced block as method body
        try:
            body_text, brace_close = _extract_balanced_block(vbody, k)
        except ValueError:
            i = name_pos + 1
            continue
        out.append((name, args_text.strip(), body_text))
        i = brace_close + 1
    return out


def pretty_print_validator(file: Path, do_simulate: bool = False, project_root: Optional[Path]=None):
    """
    Prints validator functions and the tests that call them (based on parse_tests_in_text).
    """
    try:
        text = file.read_text(encoding="utf8")
    except Exception as e:
        print(f"ERROR: cannot read {file}: {e}")
        return

    # find validator header & body
    vm = re.search(r'\bvalidator\s+([A-Za-z_]\w*)\s*{', text, re.I)
    if not vm:
        print(f"⚠️ No validator found in {file}")
        return
    vname = vm.group(1)
    open_idx = vm.end() - 1
    try:
        vbody, _ = _extract_balanced_block(text, open_idx)
    except ValueError:
        vbody = text[vm.end():]

    print(f"\n🔒 Validator: {vname}\n")

    # find functions inside validator body
    # prefer validator methods (mint/spend/else) inside the validator block
    funcs = _find_methods_in_validator_body(vbody)
    # fallback to `fn` functions in the validator body if no methods found
    if not funcs:
        funcs = _find_functions_in_text(vbody)
    if not funcs:
        print("  (no functions found inside validator; attempting project-wide lookup of referenced names...)")
        # attempt to find referenced names inside validator body and locate them project-wide
        project_root = project_root or find_project_root(file) or file.parent
        ref_names = set(re.findall(r'\b([A-Za-z_]\w*)\s*\(', vbody))
        printed_any = False
        for name in sorted(ref_names):
            found = _find_function_project_wide(project_root, name, exclude_path=file)
            if found:
                printed_any = True
                for ak_path, ln, snippet in found:
                    print(f"  🔎 Found function {name} in {_relpath_or_str(ak_path, project_root)}:{ln}")
        if not printed_any:
            print("  No referenced functions found elsewhere in the project.")
        return

    # collect tests from the file (and optionally from the whole project file-set)
    # parse tests from the same file
    #tests_in_file = parse_tests_in_text(text)

    # (optionally) parse project tests to map tests in other files to this validator
    if project_root is None:
        project_root = find_project_root(file) or file.parent

    # Use cached project tests if they exist and are for the same project root
    if _project_tests_cache is not None and _project_tests_cache_root == project_root:
        project_tests = list(_project_tests_cache)
    else:
        # build project_tests by scanning files under project_root
        project_tests = []
        for ak in project_root.rglob("*.ak"):
            try:
                ttxt = ak.read_text(encoding="utf8", errors="ignore")
            except Exception:
                continue
            parsed = parse_tests_in_text(ttxt)
            for p in parsed:
                p["_source_path"] = ak
            project_tests.extend(parsed)


    # helper to find tests that call this validator+method
    def find_tests_for_method(vname_local: str, method: str):
        """
        Return unique hits (deduplicated by test name + source path + call line).
        """
        hits = []
        seen = set()
        for t in project_tests:
            for c in t.get("calls", []):
                if c.get("validator") == vname_local and c.get("method") == method:
                    key = (t.get("name"), str(t.get("_source_path")), c.get("line"))
                    if key in seen:
                        continue
                    seen.add(key)
                    hit = dict(t)  # shallow copy
                    hit["_call"] = c
                    hits.append(hit)
        return hits


    # print each function and its narration + tests that call it
    for fname, args, body in funcs:
        args_disp = re.sub(r'\s+', ' ', args).strip()
        print(f"  🟢 {fname}({args_disp})")
        # narration heuristics
        if re.search(r'\bif\b', body) and re.search(r'\belse\b', body):
            cond_match = re.search(r'\bif\b\s+(.*?)\s*{', body, re.S)
            cond = cond_match.group(1).strip() if cond_match else "<condition>"
            print(f"     - Check: {cond}")
            print("     - → return True ✅")
            print("     - → return False ❌")
        elif re.search(r'\bTrue\b', body):
            print("     - → return True ✅")
        elif re.search(r'\bFalse\b', body):
            print("     - → return False ❌")
        elif re.search(r'\bfail\b', body):
            print("     - evaluates: fail")

        # list tests that call this method
        hits = find_tests_for_method(vname, fname)
        if hits:
            print("     Called by tests:")
            for h in hits:
                test_name = h["name"]
                src = h.get("_source_path") or file
                call = h["_call"]
                neg = call.get("negated", False)
                expectation = "should fail" if (h.get("fail_declared") or neg) else "should pass"
                print(f"       - {test_name} ({_relpath_or_str(src, project_root)}:{call['line']}) -> {expectation}")
                # show a small trace sample if present in that test
                if h.get("traces"):
                    # preserve order but remove duplicates
                    unique_traces = list(dict.fromkeys(h.get("traces", [])))
                    for tr in unique_traces[:3]:
                        print(f"           trace: {tr}")
        else:
            print("     (no tests found calling this method in project scan)")

        # simulation stub
        if do_simulate:
            print("     Execution tree (simulated):")
            if re.search(r'\bTrue\b', body):
                print("       └── return: True  [True]")
            elif re.search(r'\bFalse\b', body):
                print("       └── return: False  [False]")
            elif re.search(r'\bif\b', body):
                print("       └── branch check -> ...")


def build_report(aiken_paths: List[Path], test_log_path: Optional[Path],
                 do_simulate: bool=False, json_out: Optional[Path]=None):
    json_report = {"generated": datetime.now(timezone.utc).isoformat(), "tests": []}
    console.rule("Plutuscope - validator narration + simulation")
    global _project_tests_cache, _project_tests_cache_root
    _project_tests_cache = []
    _project_tests_cache_root = None

    # determine project_root from first file
    project_root = None
    if aiken_paths:
        project_root = find_project_root(aiken_paths[0]) or aiken_paths[0].parent

    # populate cache once for the project root (if available)
    if project_root:
        _project_tests_cache_root = project_root
        for ak in project_root.rglob("*.ak"):
            try:
                ttxt = ak.read_text(encoding="utf8", errors="ignore")
            except Exception:
                continue
            parsed = parse_tests_in_text(ttxt)
            for p in parsed:
                p["_source_path"] = ak
            _project_tests_cache.extend(parsed)

    for p in aiken_paths:
        if not p.exists():
            print(f"ERROR: missing aiken file: {p}")
            continue
        pretty_print_validator(p, do_simulate=do_simulate, project_root=project_root)
        json_report["tests"].append({"file": str(p)})
    if json_out:
        json_out.write_text(json.dumps(json_report, indent=2))


# ======================================================================
# === MAIN CLI
# ======================================================================

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--aiken', type=str, help='Path to a single .ak file')
    ap.add_argument('--tests', type=str, help='Path to aiken test log')
    ap.add_argument('--simulate', action='store_true', help='Simulate validator execution')
    ap.add_argument('--scan', type=str, help='Scan a directory recursively for .ak files')
    ap.add_argument('--no-aiken', action='store_true', help='Disable real aiken and always use mock traces')
    ap.add_argument('--instrument', action='store_true', help='Temporarily instrument project to emit trace(...) calls')
    ap.add_argument('--verbose', action='store_true', help='Verbose logging (show raw outputs)')
    args = ap.parse_args()

    if args.scan:
        ak_files = find_ak_files(args.scan)
        if not ak_files:
            rprint(f"[yellow]No .ak files found under {args.scan}")
            sys.exit(0)
        while True:
            results = analyze_files(ak_files, prefer_aiken=(not args.no_aiken), instrument=args.instrument, verbose=args.verbose)
            action = interactive_browser(results)
            if action != "rerun":
                break
        return

    if args.aiken:
        build_report([Path(args.aiken)],
                     Path(args.tests) if args.tests else None,
                     do_simulate=args.simulate)

if __name__ == "__main__":
    main()
