# l1_redeemer.py
from dataclasses import dataclass
from typing import Optional, Union
from cardano.transaction import OutputReference, Transaction, placeholder
from mocktail import mock_utxo_ref

# -------------------------------
# Redeemer type
# -------------------------------
class Redeemer:
    SuccessRedeemer = "SuccessRedeemer"
    AnotherSuccessCase = "AnotherSuccessCase"
    FailRedeemer = "FailRedeemer"
    AnotherFailCase = "AnotherFailCase"
    AnotherWayToFail = "AnotherWayToFail"
    MoreFailure = "MoreFailure"
    AnotherOne = "AnotherOne"
    AndYetAnotherOne = "AndYetAnotherOne"
    ThisOneToo = "ThisOneToo"
    AndYetAnotherOneHereToo = "AndYetAnotherOneHereToo"

# -------------------------------
# Validator
# -------------------------------
class CheckRedeemer:
    @staticmethod
    def spend(
        _datum: Optional[object],
        redeemer: str,
        _input: OutputReference,
        _tx: Transaction,
    ) -> bool:
        if redeemer in (Redeemer.SuccessRedeemer, Redeemer.AnotherSuccessCase):
            return True
        else:
            return False

    @staticmethod
    def else_(_):
        raise Exception("Validation failed")

# -------------------------------
# Tests
# -------------------------------
def test_md201_l1_test_success_redeemer():
    redeemer = Redeemer.AnotherSuccessCase
    assert CheckRedeemer.spend(None, redeemer, mock_utxo_ref(0, 0), placeholder)

def test_md201_l1_test_fail_redeemer():
    redeemer = Redeemer.AnotherWayToFail
    assert not CheckRedeemer.spend(None, redeemer, mock_utxo_ref(0, 0), placeholder)
