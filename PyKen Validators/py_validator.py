# py_validator.py
from validator_emitter import ValidatorEmitter
from type_sys import map_type


class ValidatorParser:
    def __init__(self):
        self.validators = []

    def parse(self, func):
        # Map argument types using canonical mapper
        args = []
        for arg in func["args"]:
            name = arg["name"]
            py_type = arg.get("type", "Any")
            aiken_type = map_type(py_type)
            args.append(f"{name}: {aiken_type}")

        # Re-emit function body
        emitter = ValidatorEmitter()
        for stmt in func["node"].body:
            emitter.visit(stmt)

        body_str = "\n  ".join(emitter.output)

        # Use return type from func (default is already set by py_parser)
        ret_type = func.get("ret_type", "Bool")

        validator_code = (
            f"validator {func['name']}({', '.join(args)}) -> {ret_type} {{\n"
            f"  {body_str}\n"
            f"}}"
        )

        self.validators.append({
            "name": func["name"],
            "args": args,
            "ret_type": ret_type,
            "code": validator_code,
        })
        return validator_code


class DataType:
    """Internal base for all Aiken-like types in PyKen."""
    def __init__(self, **fields):
        for k, v in fields.items():
            setattr(self, k, v)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    def __repr__(self):
        if not self.__dict__:
            return f"{self.__class__.__name__}()"
        field_str = ", ".join(f"{k}={v}" for k, v in self.__dict__.items())
        return f"{self.__class__.__name__}({field_str})"
