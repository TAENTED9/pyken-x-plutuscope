# validator_emitter.py
# Converts PyKen (Python-written Aiken-like code) -> Aiken source code.

import ast
import json
from typing import List, Tuple
from type_sys import map_type, PY_TO_AIKEN


# ---------------------------
# Helpers
# ---------------------------
def _is_camel(name: str) -> bool:
    return bool(name) and name[0].isupper()


def _str_literal(value: str) -> str:
    return json.dumps(value)


# ---------------------------
# DataType marker
# ---------------------------
class DataType:
    """Engine-side base for data holder classes (not emitted as import)."""
    def __init__(self, **fields):
        for k, v in fields.items():
            setattr(self, k, v)


# ---------------------------
# Emitter
# ---------------------------
class ValidatorEmitter(ast.NodeVisitor):
    def __init__(self):
        self.output: List[str] = []
        self.indent_level = 0
        # map type name -> list of field names
        self.type_fields = {}

    def write(self, line: str = ""):
        self.output.append(("  " * self.indent_level) + line)

    def push(self):
        self.indent_level += 1

    def pop(self):
        if self.indent_level > 0:
            self.indent_level -= 1
    
    
    def _is_docstring(self, node):
        return (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        )
    
    # ----- entrypoint -----
    def visit_Module(self, node: ast.Module):
        for stmt in node.body:
            if isinstance(stmt, ast.If):
                if (isinstance(stmt.test, ast.Compare)
                        and isinstance(stmt.test.left, ast.Name)
                        and stmt.test.left.id == "__name__"):
                    continue
            self.visit(stmt)
        return "\n".join(self.output)

    # -----  imports -----
    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            mod = alias.name.replace(".", "/")
            if alias.asname:
                self.write(f"use {mod} as {alias.asname}")
            else:
                self.write(f"use {mod}")
        return

    def visit_ImportFrom(self, node: ast.ImportFrom):
        # e.g. `from a.b import X, Y` -> `use a/b.{X, Y}` (always use braces)
        if node.module is None:
            return
        mod = node.module.replace(".", "/")
        names = []
        for alias in node.names:
            if alias.asname:
                names.append(f"{alias.name} as {alias.asname}")
            else:
                names.append(alias.name)
        self.write(f"use {mod}.{{{', '.join(names)}}}")
        return



    # ----- classes: either validator or pub type -----
    def visit_ClassDef(self, node: ast.ClassDef):
        # determines if validator class contains 'spend'/'mint'/'else_'
        method_names = {n.name for n in node.body if isinstance(n, ast.FunctionDef)}
        is_validator = any(n in method_names for n in ("spend", "mint", "else_"))

        if is_validator:
            # Emit validator block
            self.write(f"validator {node.name} {{")
            self.push()
            # emit each validator method
            for stmt in node.body:
                if isinstance(stmt, ast.FunctionDef):
                    self._emit_validator_method(stmt)
                else:
                    # ignore non-methods for validators
                    pass
            self.pop()
            self.write("}")
            # validators don't produce pub types, so no fields to record
            self.type_fields[node.name] = []
        else:
            # Emit 'pub type' for data helpers
            self.write(f"pub type {node.name} {{")
            self.push()
            # Try to find __init__ to extract field names
            init = None
            for stmt in node.body:
                if isinstance(stmt, ast.FunctionDef) and stmt.name == "__init__":
                    init = stmt
                    break
            recorded_fields = []
            if init:
                # fields are args excluding 'self'
                args = init.args.args[1:]
                if args:
                    for a in args:
                        # try to pick up annotation -> map it, fallback to Data
                        ann = None
                        if getattr(a, "annotation", None):
                            # use a robust extraction if added _annotation_name helper is added
                            ann = getattr(a.annotation, "id", None) or getattr(a.annotation, "attr", None)
                        if ann:
                            a_type = map_type(ann)
                        else:
                            # boolean-named fields
                            if a.arg.startswith("is_"):
                                a_type = "Bool"
                            else:
                                a_type = "Data"
                        self.write(f"{a.arg}: {a_type}")
                        recorded_fields.append(a.arg)
                else:
                    # no fields -> simple constructor
                    self.write(f"{node.name}")
            else:
                # no __init__ -> simple constructor
                self.write(f"{node.name}")
            self.pop()
            self.write("}")
            # store fields (may be empty list)
            self.type_fields[node.name] = recorded_fields

            
            
    # ----- helper: turn RHS into a pipeline segment -----
    def _pipeline_segment_from_rhs(self, rhs: ast.AST, var_name: str):
        """
        Given an RHS AST (an expression assigned to the tracked variable),
        return a string representing the pipeline segment or None if this 
        RHS can't be represented as a pipeline step.
        """
        if not isinstance(rhs, ast.Call):
            return None

        func = rhs.func

        # case A: tx.pipe(fn, a, b)
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == var_name and func.attr == "pipe":
            if len(rhs.args) >= 1:
                first = rhs.args[0]
                fn_expr = self._expr(first)
                other_args = [self._expr(a) for a in rhs.args[1:]] + [f"{kw.arg}={self._expr(kw.value)}" for kw in rhs.keywords]
                joined = ", ".join(a for a in other_args if a)
                return f"{fn_expr}({joined})" if joined else f"{fn_expr}()"
            return None

        # case B: fn(tx, a, b)  -> function call where first arg is the var
        if rhs.args and isinstance(rhs.args[0], ast.Name) and rhs.args[0].id == var_name:
            fn_expr = self._expr(func)
            other_args = [self._expr(a) for a in rhs.args[1:]] + [f"{kw.arg}={self._expr(kw.value)}" for kw in rhs.keywords]
            joined = ", ".join(a for a in other_args if a)
            return f"{fn_expr}({joined})" if joined else f"{fn_expr}()"

        # case C: tx.method(a, b) -> method(a, b)
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == var_name:
            method_name = func.attr
            args = [self._expr(a) for a in rhs.args] + [f"{kw.arg}={self._expr(kw.value)}" for kw in rhs.keywords]
            joined = ", ".join(a for a in args if a)
            return f"{method_name}({joined})" if joined else f"{method_name}()"

        # case D: permissive - var appears in any positional or keyword arg
        # detect occurrences of 'var_name' (as Name or as Attribute whose value is Name(var_name))
        found_var = False
        pos_args = []
        for a in rhs.args:
            if isinstance(a, ast.Name) and a.id == var_name:
                found_var = True
                continue
            if isinstance(a, ast.Attribute) and isinstance(a.value, ast.Name) and a.value.id == var_name:
                # treat tx.some_attr as presence of the var -> omit this arg so piped value will be used
                found_var = True
                continue
            pos_args.append(self._expr(a))

        kw_args = []
        for kw in rhs.keywords:
            kv = kw.value
            if isinstance(kv, ast.Name) and kv.id == var_name:
                found_var = True
                continue
            if isinstance(kv, ast.Attribute) and isinstance(kv.value, ast.Name) and kv.value.id == var_name:
                found_var = True
                continue
            kw_args.append(f"{kw.arg}={self._expr(kv)}")

        if found_var:
            fn_expr = self._expr(func)
            joined = ", ".join(p for p in (", ".join(pos_args), ", ".join(kw_args)) if p)
            return f"{fn_expr}({joined})" if joined else f"{fn_expr}()"

        # nothing matched
        return None

    def _contains_var(self, node: ast.AST, var_name: str) -> bool:
        """
        Return True if the AST node contains a reference to the variable var_name.
        We consider:
        - ast.Name with id == var_name
        - ast.Attribute whose underlying base is ast.Name(var_name), e.g. tx.foo or tx.foo.bar
        """
        for child in ast.walk(node):
            # direct name
            if isinstance(child, ast.Name) and child.id == var_name:
                return True

            # attribute chain, check base (e.g. tx.foo.bar -> base is tx)
            if isinstance(child, ast.Attribute):
                base = child
                while isinstance(base, ast.Attribute):
                    base = base.value
                if isinstance(base, ast.Name) and base.id == var_name:
                    return True

        return False

    


    # ----- helper: detect pipeline pattern in a function body -----
    def _try_emit_pipeline(self, stmts: list):
        """
        Return (start_index, assigns, base_expr_ast, segments) or None.

        - start_index: index in stmts where the pipeline chain begins
        - assigns: list of ast.Assign nodes for the var (in original order)
        - base_expr_ast: AST node for the base expression (the RHS of the first assign)
        - segments: list of pipeline segment strings (already formatted, e.g. "fn(a,b)")
        """
        if not stmts:
            return None
        last = stmts[-1]
        if not isinstance(last, ast.Return) or not isinstance(last.value, ast.Name):
            return None
        var = last.value.id

        # collect contiguous assigns to same var (immediately preceding the return)
        assigns = []
        i = len(stmts) - 2
        while i >= 0:
            s = stmts[i]
            if (isinstance(s, ast.Assign)
                and len(s.targets) == 1
                and isinstance(s.targets[0], ast.Name)
                and s.targets[0].id == var):
                assigns.insert(0, s)
                i -= 1
                continue
            break

        if not assigns:
            return None

        base_assign = assigns[0]
        base_expr_ast = base_assign.value

        # single assignment case: 'x = f(...); return x' -> no segments
        if len(assigns) == 1:
            return (i + 1, assigns, base_expr_ast, [])

        # multi-assign case: convert subsequent assigns to pipeline segments
        segments = []
        for a in assigns[1:]:
            # first try the canonical, safest conversion
            seg = self._pipeline_segment_from_rhs(a.value, var)
            if seg is not None:
                segments.append(seg)
                continue

            # second fallback (conservative): if the RHS is a Call that does NOT contain the var anywhere,
            # treat the whole call as a segment (e.g. tx = tx_in(...))
            if isinstance(a.value, ast.Call) and not self._contains_var(a.value, var):
                call_text = self._expr(a.value)
                segments.append(call_text)
                continue

            # permissive fallback: if the RHS is simple (Call, Attribute, Name, Subscript),
            # accept its textual representation as a segment. This covers patterns like:
            #   tx = tx_in(...); tx = tx_out(...); ...
            # which often don't mention 'tx' directly inside the RHS.
            if isinstance(a.value, (ast.Call, ast.Attribute, ast.Name, ast.Subscript)):
                call_text = self._expr(a.value)
                segments.append(call_text)
                continue

            # otherwise we can't safely convert this assign to a pipeline segment
            return None

        return (i + 1, assigns, base_expr_ast, segments)




    # ----- top-level function (fn / test) -----
    def visit_FunctionDef(self, node: ast.FunctionDef):
        # Skip class methods (handled separately in _emit_validator_method)
        if isinstance(getattr(node, "parent", None), ast.ClassDef):
            return

        # Tests (strip leading "test_" if present)
        if node.name.startswith("test"):
            test_name = node.name[5:] if node.name.startswith("test_") else node.name
            self.write(f"test {test_name} {{")
            self.push()
            # mark we are inside a test and start fresh name mapping for this test
            prev_in_test = getattr(self, "in_test", False)
            prev_name_map = getattr(self, "name_map", None)
            self.in_test = True
            self.name_map = {}
            for stmt in node.body:
                if not self._is_docstring(stmt):
                    self.visit(stmt)
            # restore previous flags (safety)
            self.in_test = prev_in_test
            self.name_map = prev_name_map
            self.pop()
            self.write("}")
            return

        # Generic top-level function - try to detect pipeline pattern
        pipeline = self._try_emit_pipeline(node.body)
        args = [a.arg for a in node.args.args]
        args_sig = ", ".join(args)
        # optional: detect return annotation (if track types elsewhere)
        ret_annotation = ""
        # emit function signature
        self.write(f"fn {node.name}({args_sig}){(' -> ' + node.returns.id) if getattr(node, 'returns', None) and hasattr(node.returns, 'id') else ''} {{")
        self.push()

        if pipeline:
            start_idx, assigns, base_expr_ast, segments = pipeline
            # emit any pre-statements
            for stmt in node.body[:start_idx]:
                if not self._is_docstring(stmt):
                    self.visit(stmt)

            # base expression -> convert AST to string now
            base_str = self._expr(base_expr_ast)
            self.write(base_str)
            for seg in segments:
                self.write(f"|> {seg}")

            self.pop()
            self.write("}")
            return

        # fallback: emit body normally
        for stmt in node.body:
            if not self._is_docstring(stmt):
                self.visit(stmt)
        self.pop()
        self.write("}")


    # ----- smaller statements -----
    def visit_Assign(self, node: ast.Assign):
        if len(node.targets) != 1:
            return
        target = node.targets[0]
        if isinstance(target, ast.Name):
            name = target.id

            # --- TEST: special-case x = <container>.inputs[...] or .outputs[...] -> expect [x] = <container>.inputs
            if getattr(self, "in_test", False) and isinstance(node.value, ast.Subscript):
                base = node.value.value  # e.g. tx.inputs
                # detect attr base like tx.inputs or tx.outputs
                if isinstance(base, ast.Attribute) and isinstance(base.attr, str) and base.attr in ("inputs", "outputs"):
                    base_expr = self._expr(base)  # should produce "tx.inputs"
                    norm = self._normalize_element_name(name)
                    # record name mapping for future references inside this test
                    if norm != name:
                        if not hasattr(self, "name_map") or self.name_map is None:
                            self.name_map = {}
                        self.name_map[name] = norm
                    self.write(f"expect [{norm}] = {base_expr}")
                    return
                # fallback: if textual base ends with '.inputs' or '.outputs', handle it too
                base_text = self._expr(base)
                if base_text.endswith(".inputs") or base_text.endswith(".outputs"):
                    norm = self._normalize_element_name(name)
                    if norm != name:
                        if not hasattr(self, "name_map") or self.name_map is None:
                            self.name_map = {}
                        self.name_map[name] = norm
                    self.write(f"expect [{norm}] = {base_text}")
                    return

            # If RHS is an ast.Call with a CamelCase callee -> prefer constructor assignment
            if isinstance(node.value, ast.Call):
                callee = node.value.func
                short_name = None
                if isinstance(callee, ast.Name):
                    short_name = callee.id
                elif isinstance(callee, ast.Attribute):
                    short_name = callee.attr

                if short_name and _is_camel(short_name):
                    # CASE: LHS is a CamelCase name -> user intends pattern/destructure
                    if _is_camel(name):
                        fields = self.type_fields.get(short_name)
                        if fields:
                            self.write(f"let {short_name} {{")
                            self.push()
                            for f in fields:
                                self.write(f"{f},")
                            self.pop()
                            self.write(f"}} = {name}")
                        else:
                            self.write(f"let {short_name} {{ .. }} = {name}")
                        return

                    # CASE: LHS is normal variable -> prefer 'let name = Constructor { ... }' or 'let name = Constructor(...)'
                    if node.value.keywords:
                        fields_pairs = []
                        for kw in node.value.keywords:
                            fields_pairs.append(f"{kw.arg}: {self._expr(kw.value)}")
                        record = f"{short_name} {{ {', '.join(fields_pairs)} }}"
                        self.write(f"let {name} = {record}")
                        return
                    val = self._expr(node.value)
                    self.write(f"let {name} = {val}")
                    return

            # fallback to textual expression
            val = self._expr(node.value)

            if isinstance(val, str) and (val.startswith("Datum(") or val.startswith("Data(")):
                # special case: Datum(.) or Data(.) -> destructure
                self.write(f"let Some(Datum {name}) = {val}")
            else:
                self.write(f"let {name} = {val}")
        else:
            # unsupported target form
            pass




    def visit_AnnAssign(self, node: ast.AnnAssign):
        # annotated assign like "tx: Transaction = ..." -> treat as let tx = ...
        target = node.target
        if isinstance(target, ast.Name) and node.value is not None:
            name = target.id
            val = self._expr(node.value)
            self.write(f"let {name} = {val}")

    def visit_Expr(self, node: ast.Expr):
        # expression statement (function call, etc.)
        expr_code = self._expr(node.value)
        # map python assert-expr style (calls to 'expect' would be explicit in py)
        self.write(expr_code)

    def visit_Return(self, node: ast.Return):
        if node.value is None:
            self.write("()")
        else:
            self.write(self._expr(node.value))

    def visit_If(self, node: ast.If):

        # Case: if x is None -> expect Some(x) = x
        if isinstance(node.test, ast.Compare):
            left = node.test.left
            if (isinstance(left, ast.Name)
                and isinstance(node.test.ops[0], ast.Is)
                and isinstance(node.test.comparators[0], ast.Constant)
                and node.test.comparators[0].value is None):
                varname = left.id
                self.write(f"expect Some({varname}) = {varname}")
                return

        # Try to detect pattern-match if-chain (isinstance or "in tuple/list")
        chain, final_else = self._collect_if_chain(node)
        if self._chain_is_pattern_match(chain):
            # emit "when <var> is { ... }"
            var = self._pattern_var_name(chain[0][0])
            self.write(f"when {var} is {{")
            self.push()
            for test, body in chain:
                variants = self._pattern_variants_from_test(test)
                # bodies must be single return statements
                ret_expr = self._extract_single_return_expr(body)
                for variant in variants:
                    self.write(f"{variant} -> {ret_expr}")
            # final else
            if final_else:
                # final_else is a list of stmts. Support single-return else.
                if len(final_else) == 1 and isinstance(final_else[0], ast.Return):
                    else_expr = self._expr(final_else[0].value)
                else:
                    else_expr = "False"
                self.write(f"_ -> {else_expr}")
            self.pop()
            self.write("}")
            return
        # fallback: normal boolean if -> use "if" / "else"
        test_expr = self._expr(node.test)
        self.write(f"if {test_expr} {{")
        self.push()
        for s in node.body:
            self.visit(s)
        self.pop()
        if node.orelse:
            self.write("} else {")
            self.push()
            for s in node.orelse:
                self.visit(s)
            self.pop()
        self.write("}")

    def visit_Assert(self, node: ast.Assert):
        cond = self._expr(node.test)
        self.write(f"expect {cond}")

    def visit_Raise(self, node: ast.Raise):
        # Map raises to 'fail' (best-effort)
        self.write("fail")

    def visit_Try(self, node: ast.Try):
        """
        Rewrite Python try/except into Aiken-style negation or expect False.
        """
        # Simple case: try { validator_call } except { assert True }
        if len(node.body) == 1 and isinstance(node.body[0], ast.Expr):
            expr = node.body[0].value
            if isinstance(expr, ast.Call):
                call_expr = self._expr(expr)
                # rewrite as negated call using "!" (Aiken style)
                self.write(f"!{call_expr}")
                return

        # fallback
        self.write("expect False")

    # ----- utility: emit validator class methods -----
    def _emit_validator_method(self, func: ast.FunctionDef):
        name = func.name
        # normalize else_ -> else(_)
        if name == "else_":
            self.write("else(_) {")
            self.push()
            for s in func.body:
                self.visit(s)
            self.pop()
            self.write("}")
            return
        
        # Build typed argument list
        args_parts = []
        for a in func.args.args:
            if a.arg == "_":
                args_parts.append("_")
                continue
            ann = None
            if getattr(a, "annotation", None):
                ann = getattr(a.annotation, "id", None) or getattr(a.annotation, "attr", None)
            # name-based overrides
            if a.arg in ("_datum", "datum"):
                aiken_type = "Option<Data>"
            elif a.arg in ("_redeemer", "redeemer"):
                aiken_type = "Data"
            elif ann:
                aiken_type = map_type(ann)
            else:
                aiken_type = "Data"
            args_parts.append(f"{a.arg}: {aiken_type}")

        args_sig = ", ".join(args_parts)
        self.write(f"{name}({args_sig}) {{")
        self.push()
        for s in func.body:
            if not self._is_docstring(s):
                self.visit(s)
        self.pop()
        self.write("}")

    # ----- helpers for pattern-matching detection -----
    def _normalize_element_name(self, name: str) -> str:
        """
        Normalize names used for pattern extracts in tests.
        e.g. input_item -> input, output_item -> output
        This is conservative: only common suffixes are stripped.
        """
        if name.endswith("_item"):
            return name[:-5]
        for suff in ("_input", "_output"):
            if name.endswith(suff):
                return name[: -len(suff)]
        # naive singularization for plural forms like 'inputs' -> 'input'
        if name.endswith("s") and len(name) > 1:
            return name[:-1]
        return name


    def _collect_if_chain(self, node: ast.If) -> Tuple[List[Tuple[ast.expr, List[ast.stmt]]], List[ast.stmt]]:
        chain = []
        cur = node
        while True:
            chain.append((cur.test, cur.body))
            if cur.orelse and len(cur.orelse) == 1 and isinstance(cur.orelse[0], ast.If):
                cur = cur.orelse[0]
                continue
            else:
                final_else = cur.orelse
                break
        return chain, final_else

    def _chain_is_pattern_match(self, chain: List[Tuple[ast.expr, List[ast.stmt]]]) -> bool:
        '''
        Only transform into 'when' if:
          - each test is either isinstance(var, Type) OR var in (A,B,...)
          - all tests reference same var name
          - each body is a single Return
        '''
        if not chain:
            return False
        var_name = None
        for test, body in chain:
            if not (len(body) == 1 and isinstance(body[0], ast.Return)):
                return False
            if self._pattern_var_name(test) is None:
                return False
            if var_name is None:
                var_name = self._pattern_var_name(test)
            elif self._pattern_var_name(test) != var_name:
                return False
        return True

    def _pattern_var_name(self, test: ast.expr):
        # for isinstance(x, Y) -> x
        # for x in (A,B) -> x
        if isinstance(test, ast.Call) and isinstance(test.func, ast.Name) and test.func.id == "isinstance":
            if len(test.args) >= 1 and isinstance(test.args[0], ast.Name):
                return test.args[0].id
        if isinstance(test, ast.Compare) and isinstance(test.left, ast.Name):
            # left in tuple/list
            if len(test.ops) >= 1 and isinstance(test.ops[0], ast.In):
                return test.left.id
        return None

    def _pattern_variants_from_test(self, test: ast.expr) -> List[str]:
        res = []
        if isinstance(test, ast.Call) and isinstance(test.func, ast.Name) and test.func.id == "isinstance":
            # type of second arg can be Name or Tuple of Names
            if len(test.args) >= 2:
                t = test.args[1]
                if isinstance(t, ast.Name):
                    res.append(self._constructor_name(t))
                elif isinstance(t, (ast.Tuple, ast.List)):
                    for el in t.elts:
                        if isinstance(el, ast.Name):
                            res.append(self._constructor_name(el))
        elif isinstance(test, ast.Compare) and isinstance(test.left, ast.Name):
            # left in (A,B,...)
            if len(test.ops) >= 1 and isinstance(test.ops[0], ast.In):
                comp = test.comparators[0]
                if isinstance(comp, ast.Tuple) or isinstance(comp, ast.List):
                    for el in comp.elts:
                        res.append(self._maybe_constructor_from_node(el))
                else:
                    res.append(self._maybe_constructor_from_node(comp))
        return res

    def _maybe_constructor_from_node(self, node):
        if isinstance(node, ast.Name):
            return self._constructor_name(node)
        if isinstance(node, ast.Attribute):
            # if attr is CamelCase, return attr alone
            if _is_camel(node.attr):
                return node.attr
            return f"{self._expr(node.value)}.{node.attr}"
        if isinstance(node, ast.Constant):
            return self._expr(node)
        return "<variant>"

    def _constructor_name(self, node: ast.Name):
        return node.id

    def _extract_single_return_expr(self, body: List[ast.stmt]) -> str:
        # caller ensures it's a single Return
        if body and isinstance(body[0], ast.Return):
            return self._expr(body[0].value)
        return "False"

    # ----- expression serializer (big) -----
    def _expr(self, node: ast.AST) -> str:
        """
        Serialize Python AST expression node into Aiken text.
        Special name/constructor handling:
        - Python None -> "None"
        - names/vars: 'datum', '_datum', 'data' -> "None"
        - names/vars: 'redeemer', '_redeemer' -> "Void"
        - constructors/callees: 'Datum' or 'Data' -> "None"
        - constructors/callees: 'Redeemer' -> "Void"
        Also: bytes/bytearray constants emit as string literals (decode utf-8).
        """
        # ----- constants -----
        if isinstance(node, ast.Constant):
            val = node.value
            if val is True:
                return "True"
            if val is False:
                return "False"
            # Map bytes -> string literal (remove b-prefix).
            if isinstance(val, (bytes, bytearray)):
                try:
                    s = val.decode("utf-8")
                except Exception:
                    # fall back to repr if decode fails
                    s = repr(val)
                    return s
                return _str_literal(s)
            # Always map Python None -> Aiken None (baseline)
            if val is None:
                return "None"
            if isinstance(val, str):
                return _str_literal(val)
            return repr(val)

        # ----- names (variables / simple ids) -----
        if isinstance(node, ast.Name):
            name = node.id

            # specific name-level rules requested
            if name in ("_datum", "datum", "data"):
                return "None"
            if name in ("_redeemer", "redeemer"):
                return "Void"

            # test-scoped renames (input_item -> input)
            if getattr(self, "name_map", None) and name in self.name_map:
                return self.name_map[name]

            # CamelCase names likely constructors/variants
            if _is_camel(name):
                return name
            return name

        # ----- attribute access (obj.attr) -----
        if isinstance(node, ast.Attribute):
            # map else_ attribute to ".else"
            if node.attr == "else_":
                return f"{self._expr(node.value)}.else"

            # attribute-level special mapping (e.g., obj._datum)
            if node.attr in ("_datum", "datum", "data"):
                return "None"
            if node.attr in ("_redeemer", "redeemer"):
                return "Void"

            # If attribute name is CamelCase, prefer the constructor name alone
            if _is_camel(node.attr):
                return node.attr

            return f"{self._expr(node.value)}.{node.attr}"

        # ----- function / constructor calls -----
        if isinstance(node, ast.Call):
            func_node = node.func

            # detect simple callee name when possible
            func_name = None
            if isinstance(func_node, ast.Name):
                func_name = func_node.id
            elif isinstance(func_node, ast.Attribute):
                # attribute callees like mod.Constructor -> attr part
                func_name = func_node.attr if isinstance(func_node.attr, str) else None

            # callee-level rules
            if func_name in ("Datum", "Data"):
                return "None"
            if func_name == "Redeemer":
                return "Void"

            # Option handling
            if func_name == "Some":
                inner = ", ".join(self._expr(a) for a in node.args)
                return f"Some({inner})"
            if func_name == "None":
                return "None"

            # special-case: placeholder() -> placeholder
            if isinstance(func_node, ast.Name) and func_node.id == "placeholder" and not node.args and not node.keywords:
                return "placeholder"

            # build callee textual representation
            callee_text = self._expr(func_node)

            # constructor-like: callee name is CamelCase
            short_name = callee_text.split(".")[-1]
            if _is_camel(short_name):
                if not node.args and not node.keywords:
                    return short_name
                if node.keywords:
                    fields = [f"{kw.arg}: {self._expr(kw.value)}" for kw in node.keywords]
                    return f"{short_name} {{ {', '.join(fields)} }}"
                args_inner = ", ".join(self._expr(a) for a in node.args)
                return f"{short_name}({args_inner})"

            # special-case: print -> trace @"..."
            if isinstance(func_node, ast.Name) and func_node.id == "print":
                if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    return f'trace @{_str_literal(node.args[0].value)}'

            # Generic call: simple mapping of args & kwargs
            args_list = [self._expr(a) for a in node.args]
            kwargs = ", ".join(f"{kw.arg}={self._expr(kw.value)}" for kw in node.keywords)
            joined = ", ".join(p for p in (", ".join(args_list), kwargs) if p)

            return f"{callee_text}({joined})"

        # ----- binary / boolean / unary / compare etc. -----
        if isinstance(node, ast.BinOp):
            left = self._expr(node.left)
            right = self._expr(node.right)
            op = self._binop(node.op)
            return f"{left} {op} {right}"

        if isinstance(node, ast.BoolOp):
            op = "&&" if isinstance(node.op, ast.And) else "||"
            return f" {op} ".join(self._expr(v) for v in node.values)

        if isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.Not):
                return f"!{self._expr(node.operand)}"
            if isinstance(node.op, ast.USub):
                return f"-{self._expr(node.operand)}"
            return self._expr(node.operand)

        if isinstance(node, ast.Compare):
            left = self._expr(node.left)
            if node.ops:
                op = self._cmpop(node.ops[0])
                right = self._expr(node.comparators[0])
                return f"{left} {op} {right}"
            return left

        if isinstance(node, ast.List):
            elems = ", ".join(self._expr(e) for e in node.elts)
            return f"[{elems}]"

        if isinstance(node, ast.Tuple):
            elems = ", ".join(self._expr(e) for e in node.elts)
            return f"({elems})"

        if isinstance(node, ast.Dict):
            items = []
            for k, v in zip(node.keys, node.values):
                items.append(f"{self._expr(k)}: {self._expr(v)}")
            return f"{{ {', '.join(items)} }}"

        if isinstance(node, ast.Subscript):
            # python 3.9+ slice handling: node.slice may be ast.Constant or ast.Index wrapper
            slice_node = getattr(node.slice, "value", node.slice)
            return f"{self._expr(node.value)}[{self._expr(slice_node)}]"

        if isinstance(node, ast.ListComp):
            elt = self._expr(node.elt)
            gen = node.generators[0]
            if isinstance(gen.target, ast.Name):
                target = gen.target.id
            else:
                target = self._expr(gen.target)
            iter_ = self._expr(gen.iter)
            return f"map(|{target}| {elt}, {iter_})"

        # fallback
        return "<expr>"




    def _binop(self, op):
        if isinstance(op, ast.Add): return "+"
        if isinstance(op, ast.Sub): return "-"
        if isinstance(op, ast.Mult): return "*"
        if isinstance(op, ast.Div): return "/"
        if isinstance(op, ast.Mod): return "%"
        return "?"

    def _cmpop(self, op):
        if isinstance(op, ast.Eq): return "=="
        if isinstance(op, ast.NotEq): return "!="
        if isinstance(op, ast.Lt): return "<"
        if isinstance(op, ast.LtE): return "<="
        if isinstance(op, ast.Gt): return ">"
        if isinstance(op, ast.GtE): return ">="
        if isinstance(op, ast.In): return "in"
        return "?"

# ----- Public API -----
def emit_aiken_from_source(src_text: str) -> str:
    """
    Convert PyKen Python source string into an Aiken source string.
    """
    tree = ast.parse(src_text)
    emitter = ValidatorEmitter()
    return emitter.visit(tree)


# Quick convenience when running the file manually (not required)
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            src = f.read()
        print(emit_aiken_from_source(src))
    else:
        print("# Usage: python validator_emitter.py <pyken_file.py>")
