# l5_signatures.py
from aiken.crypto import VerificationKeyHash
from cardano.transaction import OutputReference, Transaction
from cocktail import key_signed
from mocktail import (
    complete,
    mock_pub_key_hash,
    mock_utxo_ref,
    mocktail_tx,
    required_signer_hash,
)

class Datum:
    owner: VerificationKeyHash  # ByteArray in Aiken, just str here

# -------------------------------
# Validator
# -------------------------------
class check_signatures:
    @staticmethod
    def spend(
        datum_opt: Datum,
        _redeemer,
        _input: OutputReference,
        tx: Transaction,
    ) -> bool:
        if datum_opt is None:
            raise Exception("Validation failed (no datum)")
        return key_signed(tx.extra_signatories, datum_opt.owner)

    @staticmethod
    def else_(_):
        raise Exception("Validation failed")

# -------------------------------
# TestCase helper
# -------------------------------
class TestCase:
    def __init__(self, is_key_signed: bool):
        self.is_key_signed = is_key_signed

def mock_tx(test_case: TestCase) -> Transaction:
    test_case = TestCase(is_key_signed=True)
    tx = mocktail_tx()
    tx = tx.pipe(required_signer_hash, test_case.is_key_signed, mock_pub_key_hash(0))
    tx = complete(tx)
    return tx

# -------------------------------
# Tests
# -------------------------------
def test_md201_l5_test_success():
    tx = mock_tx(TestCase(True))
    datum = Datum(owner=mock_pub_key_hash(0))
    assert check_signatures.spend(datum, None, mock_utxo_ref(0, 0), tx)

def test_md201_l5_test_failed_without_signer():
    tx = mock_tx(TestCase(False))
    datum = Datum(owner=mock_pub_key_hash(0))
    assert not check_signatures.spend(datum, None, mock_utxo_ref(0, 0), tx)

def test_md201_l5_test_failed_with_incorrect_signer():
    tx = mock_tx(TestCase(True))
    datum = Datum(owner=mock_pub_key_hash(1))
    assert not check_signatures.spend(datum, None, mock_utxo_ref(0, 0), tx)

def test_md201_l5_test_failed_with_no_datum():
    tx = mock_tx(TestCase(True))
    try:
        check_signatures.spend(None, None, mock_utxo_ref(0, 0), tx)
        assert False
    except Exception:
        assert True
