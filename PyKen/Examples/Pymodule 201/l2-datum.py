# l2_datum.py
from dataclasses import dataclass
from typing import Optional
from cardano.transaction import OutputReference, Transaction, placeholder
from mocktail import mock_utxo_ref

# -------------------------------
# Datum & Redeemer
# -------------------------------
@dataclass
class Datum1:
    secret: str

class Datum2:
    pass

@dataclass
class RedeemerWithMessage:
    message: str

# -------------------------------
# Validator
# -------------------------------
class CheckDatum:
    @staticmethod
    def spend(
        datum_opt: Optional[object],
        redeemer: RedeemerWithMessage,
        _input: OutputReference,
        _tx: Transaction,
    ) -> bool:
        if isinstance(datum_opt, Datum1):
            return redeemer.message == datum_opt.secret
        return False

    @staticmethod
    def else_(_):
        raise Exception("Validation failed")

# -------------------------------
# Tests
# -------------------------------
def test_md201_l2_test_success():
    datum = Datum1(secret="hello world")
    redeemer = RedeemerWithMessage(message="hello world")
    assert CheckDatum.spend(datum, redeemer, mock_utxo_ref(0, 0), placeholder)

def test_md201_l2_test_fail_with_incorrect_redeemer_message():
    datum = Datum1(secret="hello world")
    redeemer = RedeemerWithMessage(message="GM Cardano")
    assert not CheckDatum.spend(datum, redeemer, mock_utxo_ref(0, 0), placeholder)

def test_md201_l2_test_fail_with_fail_datum():
    datum = Datum2()
    redeemer = RedeemerWithMessage(message="hello world")
    assert not CheckDatum.spend(datum, redeemer, mock_utxo_ref(0, 0), placeholder)
