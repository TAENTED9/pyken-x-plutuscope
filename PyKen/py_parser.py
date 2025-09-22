# py_parser.py
import ast
from type_sys import map_type

class FunctionParser(ast.NodeVisitor):
    def __init__(self):
        self.funcs = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        #args = []
        #for arg in node.args.args:
            # Extract annotation name if present
        #    if arg.annotation:
        #        ann = getattr(arg.annotation, "id", None) or getattr(arg.annotation, "attr", None)
        #        aiken_type = map_type(ann)
        #    else:
                # No annotation -> default to Data (generic)
        #        aiken_type = "Data"
        #    args.append({"name": arg.arg, "type": aiken_type})

        # Return type: if annotated, map it; otherwise default to Bool (validators often return Bool)
        if isinstance(getattr(node, "parent", None), ast.ClassDef):
            return
        if node.returns:
            ret_ann = getattr(node.returns, "id", None) or getattr(node.returns, "attr", None)
            ret_type = map_type(ret_ann)
        else:
            ret_type = "Bool"

        decorators = []
        for d in node.decorator_list:
            if isinstance(d, ast.Name):
                decorators.append(d.id)
            elif isinstance(d, ast.Attribute):
                decorators.append(d.attr)

        # Keep the original AST node so emitters can operate on it directly
        self.funcs.append({
            "name": node.name,
            "body": node.body,
            "ret_type": ret_type,
            "decorators": decorators,
            "node": node,
        })

