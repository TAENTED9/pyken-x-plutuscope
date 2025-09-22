# fn_emitter
'''
Emit simple Aiken functions from Python AST.   
'''
import ast
import sys
from collections import Counter

# --- Operators & constants mapping ---
OPS = {
    ast.Eq: "==",
    ast.NotEq: "!=",
    ast.Gt: ">",
    ast.Lt: "<",
    ast.GtE: ">=",
    ast.LtE: "<=",
}

CONSTANTS_MAP = {
    2.718: "e",
    1.618: "phi"
}

# --- Python -> Aiken type mapping ---
def emit_type(py_type: str) -> str:
    mapping = {
        "int": "Int",
        "float": "Int",    # Aiken doesn’t have float
        "bool": "Bool",
        "str": "String",
        "None": "Void",
        "Any": "_",
        "object": "_",
    }
    return mapping.get(py_type, "_")


# --- AST-based type inference ---
def infer_type_from_ast(node) -> str:
    """Infer Aiken type from an ast.Constant node (or fallback)."""
    if isinstance(node, ast.Constant):
        v = node.value
        if isinstance(v, bool):
            return "Bool"
        if isinstance(v, int):
            return "Int"
        if isinstance(v, float):
            return "Int"
        if isinstance(v, str):
            return "String"
        if v is None:
            return "Void"
    return "_"


def infer_type_from_expr(node) -> str:
    """Try to infer a type from an arbitrary AST expression."""
    if isinstance(node, ast.Constant):
        return infer_type_from_ast(node)
    if isinstance(node, (ast.Compare, ast.BoolOp)):
        return "Bool"
    if isinstance(node, ast.UnaryOp):
        return infer_type_from_expr(node.operand)
    if isinstance(node, ast.BinOp):
        # Try to infer from child nodes
        left_t = infer_type_from_expr(node.left)
        right_t = infer_type_from_expr(node.right)
        if isinstance(node.op, ast.Add):
            # string concat or numeric add
            if left_t == right_t and left_t != "_":
                return left_t
            if left_t != "_" and right_t == "_":
                return left_t
            if right_t != "_" and left_t == "_":
                return right_t
        # for other ops, numeric => Int
        if left_t == "Int" or right_t == "Int":
            return "Int"
        return "_"
    if isinstance(node, ast.Call):
        # Detect builtin casts: int(), str(), bool()
        if isinstance(node.func, ast.Name):
            fn = node.func.id
            if fn == "int":
                return "Int"
            if fn == "str":
                return "String"
            if fn == "bool":
                return "Bool"
        return "_"
    if isinstance(node, ast.Name):
        return "_"  # unknown without context
    return "_"


def infer_param_type_from_body(param_name: str, func_body) -> str:
    """
    Heuristic scan of the function body AST to infer a parameter's type.
    Looks for:
     - param used directly in a boolean test -> Bool
     - param compared to a constant -> type of that constant
     - param used in BinOp with a constant -> attempts to infer from that constant
    """
    # wrap in an AST Module for ast.walk
    module = ast.Module(body=func_body, type_ignores=[])
    for node in ast.walk(module):
        # If param used as a boolean condition: `if flag:` or in BoolOp
        if isinstance(node, ast.If):
            t = node.test
            if isinstance(t, ast.Name) and t.id == param_name:
                return "Bool"
            # boolop directly containing the name
            if isinstance(t, ast.BoolOp):
                for v in t.values:
                    if isinstance(v, ast.Name) and v.id == param_name:
                        return "Bool"

        # Comparisons: n == 0  or 0 == n
        if isinstance(node, ast.Compare):
            left = node.left
            comps = node.comparators
            if isinstance(left, ast.Name) and left.id == param_name:
                # check comparators for constants
                for c in comps:
                    if isinstance(c, ast.Constant):
                        return infer_type_from_ast(c)
            for c in comps:
                if isinstance(c, ast.Name) and c.id == param_name:
                    if isinstance(left, ast.Constant):
                        return infer_type_from_ast(left)

        # BinOp: param + 5  or 5 + param
        if isinstance(node, ast.BinOp):
            l = node.left
            r = node.right
            if isinstance(l, ast.Name) and l.id == param_name and isinstance(r, ast.Constant):
                return infer_type_from_ast(r)
            if isinstance(r, ast.Name) and r.id == param_name and isinstance(l, ast.Constant):
                return infer_type_from_ast(l)

        # direct name in boolean expressions
        if isinstance(node, ast.BoolOp):
            for v in node.values:
                if isinstance(v, ast.Name) and v.id == param_name:
                    return "Bool"

    return "_"


# --- Helpers for values & conditions ---
def format_value(val):
    """Format Python constant values to Aiken-friendly textual representation."""
    if isinstance(val, (int, float)):
        return CONSTANTS_MAP.get(val, str(val))
    if isinstance(val, str):
        return f"\"{val}\""
    if val is None:
        return "None"
    return str(val)


def _normalize_unparse_string(s: str) -> str:
    """
    Convert unparsed Python string literal single-quotes to double-quotes
    (ast.unparse may produce single quotes).
    """
    if not isinstance(s, str):
        return s
    if len(s) >= 2 and s[0] == "'" and s[-1] == "'":
        return '"' + s[1:-1].replace('"', '\\"') + '"'
    return s


def render_expr(node):
    """
    Render an AST expression to Aiken text:
     - constants get formatted with quotes if needed
     - other expressions use ast.unparse but with string normalization
    """
    if isinstance(node, ast.Constant):
        return format_value(node.value)
    # fall back to unparsed expression for names, binops, calls, etc.
    try:
        s = ast.unparse(node)
    except Exception:
        s = "<unparse-error>"
    return _normalize_unparse_string(s)


def transpile_condition(test):
    """Turn Python condition AST into Aiken condition string."""
    # Handle chained comparisons (e.g., a < b < c)
    if isinstance(test, ast.Compare):
        left = ast.unparse(test.left)
        parts = []
        for op, comp in zip(test.ops, test.comparators):
            op_str = OPS.get(type(op), None)
            try:
                comp_val = eval(compile(ast.Expression(comp), '', 'eval'))
                right = format_value(comp_val)
            except Exception:
                right = _normalize_unparse_string(ast.unparse(comp))
            parts.append(f"{left} {op_str} {right}")
            left = ast.unparse(comp)
        return " and ".join(parts)
    # Handle boolean operations (and/or)
    elif isinstance(test, ast.BoolOp):
        op = "and" if isinstance(test.op, ast.And) else "or"
        return f" {op} ".join([transpile_condition(v) for v in test.values])
    elif isinstance(test, ast.Name):
        return test.id
    elif isinstance(test, ast.Constant) and isinstance(test.value, bool):
        return "True" if test.value else "False"
    return _normalize_unparse_string(ast.unparse(test))


def collect_results_from_if(if_node, results):
    """Recursively collect the 'result' expression nodes from an If/Elif/Else chain."""
    # check the main if body
    for s in if_node.body:
        if isinstance(s, ast.Return):
            results.append(s.value)
        elif isinstance(s, ast.Expr):
            results.append(s.value)
    # handle orelse: could be nested If (elif) or a list of statements for else
    if if_node.orelse:
        # elif chain: single node which is an If
        if len(if_node.orelse) == 1 and isinstance(if_node.orelse[0], ast.If):
            collect_results_from_if(if_node.orelse[0], results)
        else:
            # else block: scan returns or exprs there
            for s in if_node.orelse:
                if isinstance(s, ast.Return):
                    results.append(s.value)
                elif isinstance(s, ast.Expr):
                    results.append(s.value)


# --- Unified function emitter ---
def emit_function(func, annotations=None) -> str:
    """
    Emit an Aiken function from a parsed Python AST + optional type hints.
    - func: dict with keys 'name', 'args', 'body' (from AST parsing)
      where func['args'] is a list of (name, default_node_or_None) OR list of dicts {'name':..., ...}
    - annotations: optional dict mapping arg names -> either type object or string
    """
    # 1) Param types: use annotations -> default values -> inference from body
    param_types = {}
    # build an AST module wrapper for body scanning
    module = ast.Module(body=func["body"], type_ignores=[])

    # helper to normalize annotation values (type object or string -> string)
    def annotation_to_str(av):
        if isinstance(av, str):
            return av
        if isinstance(av, type):
            return av.__name__
        return None

    # func["args"] may be list of tuples (name, default) OR dicts {"name":..., ...}
    args_list = func.get("args", [])

    # --- Normalize argument names and defaults into a list of (name, default) tuples ---
    normalized_args = []
    for item in args_list:
        if isinstance(item, (list, tuple)):
            name, default = item[0], item[1]
        elif isinstance(item, dict):
            name = item.get("name")
            default = item.get("default", None)
        else:
            # fallback: stringify but keep None default
            name = str(item)
            default = None
        normalized_args.append((name, default))

    # build a simple list of arg names for later use
    arg_names = [n for n, _ in normalized_args]

    # Infer param types
    for name, default in normalized_args:
        # annotation from provided annotations dict (if any)
        if annotations and name in annotations:
            ann = annotation_to_str(annotations[name])
            if ann:
                param_types[name] = emit_type(ann)
                continue

        # default value inference
        if default is not None:
            inferred = infer_type_from_ast(default)
            if inferred != "_":
                param_types[name] = inferred
                continue

        # heuristic from body usage
        inferred = infer_param_type_from_body(name, func["body"])
        param_types[name] = inferred

    # 2) Collect possible return result expressions (from Return and If branches)
    result_nodes = []
    for stmt in func["body"]:
        if isinstance(stmt, ast.Return):
            if stmt.value is not None:
                result_nodes.append(stmt.value)
        elif isinstance(stmt, ast.If):
            collect_results_from_if(stmt, result_nodes)

    # 3) Infer return type from result_nodes (choose unanimous non '_' type when possible)
    inferred_return_types = [infer_type_from_expr(n) for n in result_nodes if n is not None]
    return_type_str = "_"
    if annotations and "return" in annotations:
        ann = annotation_to_str(annotations["return"])
        if ann:
            return_type_str = emit_type(ann)
    elif inferred_return_types:
        # pick the most common non-'_' type if consistent
        non_unders = [t for t in inferred_return_types if t != "_"]
        if non_unders:
            most_common = Counter(non_unders).most_common(1)[0][0]
            return_type_str = most_common
        else:
            return_type_str = "_"

    # 4) Build header (use normalized arg names)
    params = [f"{n}: {param_types.get(n,'_')}" for n in arg_names]
    header = f"fn {func['name']}({', '.join(params)}) -> {return_type_str} {{"

    # 5) Emit body lines
    body_lines = []
    handled_if = False

    # anchor_arg extraction: safe from normalized_args
    if arg_names:
        anchor_arg = arg_names[0]
    else:
        anchor_arg = "_"

    for stmt in func["body"]:
        if isinstance(stmt, ast.If):
            handled_if = True
            cond = transpile_condition(stmt.test)
            # main if branch: find first return or expr
            main_result = None
            for s in stmt.body:
                if isinstance(s, ast.Return):
                    main_result = s.value
                    break
                elif isinstance(s, ast.Expr):
                    main_result = s.value
                    break
            if main_result is not None:
                body_lines.append(f"    {cond} -> {render_expr(main_result)}")
            else:
                body_lines.append(f"    {cond} -> /* no result */")

            # handle elif/else (flatten chain)
            if len(stmt.orelse) == 1 and isinstance(stmt.orelse[0], ast.If):
                current = stmt.orelse[0]
                while isinstance(current, ast.If):
                    cond = transpile_condition(current.test)
                    main_result = None
                    for s in current.body:
                        if isinstance(s, ast.Return):
                            main_result = s.value
                            break
                        elif isinstance(s, ast.Expr):
                            main_result = s.value
                            break
                    if main_result is not None:
                        body_lines.append(f"    {cond} -> {render_expr(main_result)}")
                    else:
                        body_lines.append(f"    {cond} -> /* no result */")
                    if len(current.orelse) == 1 and isinstance(current.orelse[0], ast.If):
                        current = current.orelse[0]
                    else:
                        # final else block (if present)
                        if current.orelse:
                            else_result = None
                            for s in current.orelse:
                                if isinstance(s, ast.Return):
                                    else_result = s.value
                                    break
                                elif isinstance(s, ast.Expr):
                                    else_result = s.value
                                    break
                            if else_result is not None:
                                body_lines.append(f"    else (_) {{ {render_expr(else_result)} }}")
                            else:
                                body_lines.append(f"    else (_) {{ /* no result */ }}")
                        break
            else:
                # direct else block (list)
                if stmt.orelse:
                    else_result = None
                    for s in stmt.orelse:
                        if isinstance(s, ast.Return):
                            else_result = s.value
                            break
                        elif isinstance(s, ast.Expr):
                            else_result = s.value
                            break
                    if else_result is not None:
                        body_lines.append(f"    else (_) {{ {render_expr(else_result)} }}")
                    else:
                        body_lines.append(f"    else (_) {{ /* no result */ }}")

        elif isinstance(stmt, ast.Return):
            if stmt.value is not None:
                body_lines.append(f"  {render_expr(stmt.value)}")
            else:
                body_lines.append("  /* return */")
        else:
            # For unsupported statements we include a comment to help debugging
            body_lines.append(f"  // Unsupported statement: {type(stmt).__name__}")

    # 6) Assemble function text
    if handled_if:
        return "\n".join([
            header,
            f"  when {anchor_arg} {{",
            *body_lines,
            "  }",
            "}"
        ])
    else:
        return "\n".join([header, *body_lines, "}"])




# --- Helpers to parse a Python function into the expected 'func' dict ---
def parse_functions_from_source(source: str):
    """
    Parse Python source and return a list of func dicts:
    func: { 'name': str, 'args': [(name, default_node_or_None), ...], 'body': [ast nodes...] }
    Also returns an 'annotations' dict mapping arg names / 'return' -> annotation string (if present)
    """
    tree = ast.parse(source)
    result = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            # args + defaults alignment
            args = []
            all_args = node.args.args  # list of ast.arg
            defaults = node.args.defaults or []
            num_args = len(all_args)
            num_defaults = len(defaults)
            default_start = num_args - num_defaults
            for i, a in enumerate(all_args):
                if i >= default_start:
                    default_node = defaults[i - default_start]
                else:
                    default_node = None
                args.append((a.arg, default_node))

            # gather annotations (as strings or None)
            annotations = {}
            for a in all_args:
                if a.annotation is not None:
                    annotations[a.arg] = ast.unparse(a.annotation)
            if node.returns is not None:
                annotations["return"] = ast.unparse(node.returns)

            func = {
                "name": node.name,
                "args": args,
                "body": node.body
            }
            result.append((func, annotations))
    return result


# --- If run as script, transpile file or demo examples ---
if __name__ == "__main__":
    if len(sys.argv) > 1:
        path = sys.argv[1]
        with open(path, "r", encoding="utf-8") as f:
            src = f.read()
        funcs = parse_functions_from_source(src)
    else:
        # Demo functions (useful for quick test)
        src = """
def foo(x, y):
    if x == 2 and y == 3:
        return "x + y"

def bar(flag):
    if flag:
        return "hi"
    else:
        return "bye"

def describe_number(n):
    if n == 0:
        return "zero"
    elif n == 1:
        return "one"
"""
        funcs = parse_functions_from_source(src)

    for func, ann in funcs:
        # normalize annotation values: currently strings from ast.unparse
        normalized_ann = {}
        for k, v in ann.items():
            normalized_ann[k] = v  # string like "int", "str" or expressions
        out = emit_function(func, annotations=normalized_ann)
        print(out)
        print()  # blank line between functions
