# cardano/assets.py
from dataclasses import dataclass, asdict
from typing import Dict, Tuple, List

# --- Aliases (simple wrappers) ---
AssetName = bytes   # alias for ByteArray
Lovelace = int
PolicyId = str      # in Aiken it's Hash<Blake2b_224, Script>

# --- Constants ---
ada_asset_name: AssetName = b""
ada_policy_id: PolicyId = ""
zero: "Value"  # defined after Value

@dataclass
class Value:
    lovelace: Lovelace = 0
    tokens: Dict[Tuple[PolicyId, AssetName], int] = None

    def __post_init__(self):
        if self.tokens is None:
            self.tokens = {}

    def to_dict(self):
        return {"lovelace": self.lovelace, "tokens": {
            f"{pid}:{an.decode('utf-8','ignore')}": q
            for (pid, an), q in self.tokens.items()
        }}

# --- Constructors ---
def from_asset(policy_id: PolicyId, asset_name: AssetName, quantity: int) -> Value:
    v = Value()
    v.tokens[(policy_id, asset_name)] = quantity
    return v

def from_asset_list(xs: List[Tuple[PolicyId, List[Tuple[AssetName, int]]]]) -> Value:
    v = Value()
    for pid, assets in xs:
        for an, qty in assets:
            v.tokens[(pid, an)] = qty
    return v

def from_lovelace(quantity: int) -> Value:
    return Value(lovelace=quantity)

# --- Inspecting ---
def is_zero(v: Value) -> bool:
    return v.lovelace == 0 and all(q == 0 for q in v.tokens.values())

def lovelace_of(v: Value) -> int:
    return v.lovelace

def quantity_of(v: Value, pid: PolicyId, an: AssetName) -> int:
    return v.tokens.get((pid, an), 0)

def tokens(v: Value, pid: PolicyId) -> Dict[AssetName, int]:
    return {an: q for (p, an), q in v.tokens.items() if p == pid}

def policies(v: Value) -> List[PolicyId]:
    return list({p for (p, _) in v.tokens.keys()})

# --- Combining ---
def add(v: Value, pid: PolicyId, an: AssetName, q: int) -> Value:
    v.tokens[(pid, an)] = v.tokens.get((pid, an), 0) + q
    return v

def merge(left: Value, right: Value) -> Value:
    result = Value(lovelace=left.lovelace + right.lovelace, tokens=dict(left.tokens))
    for k, q in right.tokens.items():
        result.tokens[k] = result.tokens.get(k, 0) + q
    return result

def negate(v: Value) -> Value:
    return Value(lovelace=-v.lovelace, tokens={k: -q for k, q in v.tokens.items()})

def without_lovelace(v: Value) -> Value:
    return Value(lovelace=0, tokens=dict(v.tokens))

# finalize zero
zero = Value()
