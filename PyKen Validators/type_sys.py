# type_sys.py
# Centralized type mapping & helpers for PyKen → Aiken

# ----------------------------------------------------------
# Python → Aiken type mapping
# ----------------------------------------------------------
PY_TO_AIKEN = {
    # Python builtins
    "int": "Int",
    "str": "String",
    "bool": "Bool",
    "float": "Int",          # No float in Aiken; map to Int
    "bytes": "ByteArray",
    "Any": "Data",
    "Data": "Data",
    "None": "None",

    # Python containers
    "dict": "Dict<Data, Data>",
    "list": "List<Data>",
    "tuple": "Pair<Data, Data>",

    # Special Aiken-like aliases
    "Datum": "Option<Data>",
    "Redeemer": "Data",
    "Context": "ScriptContext",

    # Cardano-specific (from your stdlib mirror)
    "PolicyId": "PolicyId",
    "Value": "Value",
    "Address": "Address",
    "Output": "Output",
    "Input": "Input",
    "OutputReference": "OutputReference",
    "Transaction": "Transaction",
    "ScriptContext": "ScriptContext",
    "Credential": "Credential",
}


# ----------------------------------------------------------
# Universal fallback handler
# ----------------------------------------------------------
def map_type(py_type: str) -> str:
    """
    Map a Python type hint to Aiken type.
    Falls back to Data for unknown types,
    unless it looks like a custom PyKen data class.
    """
    if py_type in PY_TO_AIKEN:
        return PY_TO_AIKEN[py_type]

    # Heuristic: if it starts with capital, treat as custom Aiken type
    if py_type and py_type[0].isupper():
        return py_type

    # Fallback
    return "Data"


# ----------------------------------------------------------
# Internal PyKen Type system (for unification logic)
# ----------------------------------------------------------
class Type:
    INT = "Int"
    FLOAT = "Float"
    STRING = "String"
    BOOL = "Bool"
    ANY = "Any"
    VOID = "Void"


def unify(t1, t2):
    """
    Try to unify two types.
    - Same → itself
    - Any → other
    - Void → other
    - Int vs Float → Float
    - Fallback → Any
    """
    if t1 == t2:
        return t1
    if t1 == Type.ANY:
        return t2
    if t2 == Type.ANY:
        return t1
    if t1 == Type.VOID:
        return t2
    if t2 == Type.VOID:
        return t1
    if (t1, t2) in [(Type.INT, Type.FLOAT), (Type.FLOAT, Type.INT)]:
        return Type.FLOAT
    return Type.ANY
