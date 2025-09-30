# validators/always_succeed_mint.py

from cardano.assets import PolicyId
from cardano.transaction import Transaction, placeholder
from aiken.crypto import Data  # alias: bytes

# --- Validator: always_succeed ---

class always_succeed:
    @staticmethod
    def mint(_redeemer: Data, _policy_id: PolicyId, _tx: Transaction) -> bool:
        return True

    @staticmethod
    def else_(context) -> None:
        raise Exception("fail")  # Aiken's `fail` → Python exception


# --- Tests ---

def test_m102_always_succeed_minting_policy():
    # just call the validator with Void, empty policy, and placeholder tx
    always_succeed.mint(None, "", placeholder())
