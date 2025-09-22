# l7_inputs_outputs.py
from cardano.assets import from_lovelace
from cardano.transaction import OutputReference, Transaction
from mocktail import (
    complete,
    mock_pub_key_address,
    mock_script_address,
    mock_tx_hash,
    mock_utxo_ref,
    mocktail_tx,
    tx_in,
    tx_out,
)

# -------------------------------
# Validator
# -------------------------------
class CheckOnlyScriptInput:
    @staticmethod
    def spend(
        _datum,
        _redeemer,
        _input: OutputReference,
        tx: Transaction,
    ) -> bool:
        return len(tx.inputs) == 1 and len(tx.outputs) == 1

    @staticmethod
    def else_(_):
        raise Exception("Validation failed")

# -------------------------------
# TestCase helper
# -------------------------------
class TestCase:
    def __init__(self, is_input_present, is_single_input, is_output_present, is_single_output):
        self.is_input_present = is_input_present
        self.is_single_input = is_single_input
        self.is_output_present = is_output_present
        self.is_single_output = is_single_output

def mock_tx(test_case: TestCase) -> Transaction:
    test_case = TestCase(True, True, True, True)
    tx = mocktail_tx()
    tx = tx_in(test_case.is_input_present, mock_tx_hash(0), 0, from_lovelace(1_000_000), mock_script_address(0, None))
    tx = tx_in(not test_case.is_single_input, mock_tx_hash(0), 1, from_lovelace(1_000_000), mock_script_address(0, None))
    tx = tx_in(not test_case.is_single_input, mock_tx_hash(0), 2, from_lovelace(1_000_000), mock_script_address(0, None))
    tx = tx_out(test_case.is_output_present, mock_pub_key_address(0, None), from_lovelace(1_000_000))
    tx = tx_out(not test_case.is_single_output, mock_pub_key_address(0, None), from_lovelace(1_000_000))
    tx = tx_out(not test_case.is_single_output, mock_pub_key_address(0, None), from_lovelace(1_000_000))
    tx = complete(tx)
    return tx

# -------------------------------
# Tests
# -------------------------------
def test_md201_l7_test_success():
    tx = mock_tx(TestCase(True, True, True, True))
    assert CheckOnlyScriptInput.spend(None, None, mock_utxo_ref(0, 0), tx)

def test_md201_l7_test_fail_with_no_input():
    tx = mock_tx(TestCase(False, True, True, True))
    assert not CheckOnlyScriptInput.spend(None, None, mock_utxo_ref(0, 0), tx)

def test_md201_l7_test_fail_with_multiple_input():
    tx = mock_tx(TestCase(True, False, True, True))
    assert not CheckOnlyScriptInput.spend(None, None, mock_utxo_ref(0, 0), tx)

def test_md201_l7_test_fail_with_no_output():
    tx = mock_tx(TestCase(True, True, False, True))
    assert not CheckOnlyScriptInput.spend(None, None, mock_utxo_ref(0, 0), tx)

def test_md201_l7_test_fail_with_multiple_output():
    tx = mock_tx(TestCase(True, True, True, False))
    assert not CheckOnlyScriptInput.spend(None, None, mock_utxo_ref(0, 0), tx)
