# validators/l0_mock_tx.py

from cardano.assets import PolicyId
from cardano.transaction import OutputReference, Transaction, placeholder
from aiken.crypto import Data
from mocktail import complete, mock_utxo_ref, mocktail_tx


# === Transaction Placeholder ===
def transaction_placeholder() -> Transaction:
    return placeholder()


# === Validator: always_succeed ===
class always_succeed:
    @staticmethod
    def mint(_redeemer: Data, _policy_id: PolicyId, _tx: Transaction) -> bool:
        return True

    @staticmethod
    def spend(
        _datum: Data,
        _redeemer: Data,
        _input: OutputReference,
        _tx: Transaction,
    ) -> bool:
        return True

    @staticmethod
    def else_(context) -> None:
        raise Exception("fail")


# === Tests ===
def test_m103_l0_aiken_builtin_placeholder():
    assert transaction_placeholder() == placeholder()


def test_m103_l0_aiken_mocktail_tx():
    tx = complete(mocktail_tx())
    assert placeholder() == tx


def test_m103_l0_always_succeed_minting_policy():
    always_succeed.mint(None, "", placeholder())


def test_m103_l0_always_succeed_spending_validator():
    input_ref = OutputReference(
        transaction_id="cd82a190d3b4ef95a50bd791882959f541e308adb69b12d022d94a6d9f02bcf0",
        output_index=0,
    )
    always_succeed.spend(None, None, input_ref, placeholder())


def test_m103_l0_mocktail_mock_utxo_ref():
    assert mock_utxo_ref(0, 0) == OutputReference(
        transaction_id="cd82a190d3b4ef95a50bd791882959f541e308adb69b12d022d94a6d9f02bcf0",
        output_index=0,
    )
