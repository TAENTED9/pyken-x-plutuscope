# validators/always_succeed_spend.py

from cardano.transaction import OutputReference, Transaction, placeholder
from cardano.script_context import ScriptContext, ScriptInfo
from aiken.crypto import Data
from mocktail import mock_utxo_ref


# === Validator: always_succeed ===
class always_succeed:
    @staticmethod
    def spend(
        _datum: Data,  # Option<Data> simplified as None|bytes
        _redeemer: Data,
        _input: OutputReference,
        _tx: Transaction,) -> bool:
        return True

    @staticmethod
    def else_(context: ScriptContext) -> None:
        raise Exception("fail")


# === Tests ===
def test_m102_always_succeed_spending_validator():
    print("validate for any spending transaction")
    always_succeed.spend(None, None, mock_utxo_ref(0, 0), placeholder())


def test_m102_fail_always_succeed_spending_validator():
    context = ScriptContext(
        transaction=placeholder(),
        redeemer=None,
        info=ScriptInfo.Minting(""),
    )
    try:
        always_succeed.else_(context)
    except Exception:
        assert True
    else:
        assert False
