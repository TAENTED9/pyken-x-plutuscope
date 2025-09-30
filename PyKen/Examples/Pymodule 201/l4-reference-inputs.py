# l4_reference_inputs.py
from typing import Optional
from cardano.assets import from_lovelace
from cardano.transaction import OutputReference, Transaction
from mocktail import (
    complete,
    mock_pub_key_address,
    mock_tx_hash,
    mock_utxo_ref,
    mocktail_tx,
    ref_tx_in,
    tx_in,
    tx_out,
)

# -------------------------------
# Validator
# -------------------------------
class CheckReferenceInputs:
    @staticmethod
    def spend(
        _datum_opt: Optional[object],
        _redeemer: object,
        _input: OutputReference,
        tx: Transaction,
    ) -> bool:
        return len(tx.reference_inputs) == 1

    @staticmethod
    def else_(_):
        raise Exception("Validation failed")

# -------------------------------
# TestCase helper
# -------------------------------
class TestCase:
    def __init__(self, is_ref_input_present: bool, is_multiple_ref_inputs: bool):
        self.is_ref_input_present = is_ref_input_present
        self.is_multiple_ref_inputs = is_multiple_ref_inputs

def mock_tx(test_case: TestCase) -> Transaction:
    tx = mocktail_tx()
    tx = tx.pipe(ref_tx_in, test_case.is_ref_input_present, mock_tx_hash(0), 1, from_lovelace(1_000_000), mock_pub_key_address(0, None))
    tx = tx.pipe(ref_tx_in, test_case.is_multiple_ref_inputs, mock_tx_hash(0), 2, from_lovelace(5_000_000), mock_pub_key_address(0, None))
    tx = tx.pipe(ref_tx_in, test_case.is_multiple_ref_inputs, mock_tx_hash(0), 3, from_lovelace(3_000_000), mock_pub_key_address(0, None))
    tx = tx.pipe(complete)
    return tx

# -------------------------------
# Tests
# -------------------------------
def test_md201_l4_test_success():
    tx = mock_tx(TestCase(True, False))
    assert CheckReferenceInputs.spend(None, None, mock_utxo_ref(0, 0), tx)

def test_md201_l4_test_fail_with_no_ref_input():
    tx = mock_tx(TestCase(False, False))
    assert not CheckReferenceInputs.spend(None, None, mock_utxo_ref(0, 0), tx)

def test_md201_l4_test_fail_with_multiple_ref_input():
    tx = mock_tx(TestCase(False, True))
    assert not CheckReferenceInputs.spend(None, None, mock_utxo_ref(0, 0), tx)
