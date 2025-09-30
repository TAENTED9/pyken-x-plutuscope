# l6_time.py
from cocktail import valid_before, valid_after
from cardano.transaction import OutputReference, Transaction
from mocktail import (
    complete,
    invalid_before,
    invalid_hereafter,
    mock_utxo_ref,
    mocktail_tx,
    tx_in,
    tx_out,
)

# -------------------------------
# Utility (cocktail.valid_before/after)
# -------------------------------
class Datum:
    must_be_after: int  
    must_be_before: int
    
def valid_before(validity_range, upper: int) -> bool:
    return validity_range.upper is not None and validity_range.upper <= upper

def valid_after(validity_range, lower: int) -> bool:
    return validity_range.lower is not None and validity_range.lower >= lower

# -------------------------------
# Validator
# -------------------------------
class CheckTime:
    @staticmethod
    def spend(
        datum_opt: Datum,
        _redeemer,
        _input: OutputReference,
        tx: Transaction,
    ) -> bool:
        if datum_opt is None:
            raise Exception("Validation failed (no datum)")
        is_upper = valid_before(tx.validity_range, datum_opt.must_be_before)
        is_lower = valid_after(tx.validity_range, datum_opt.must_be_after)
        return is_upper and is_lower

    @staticmethod
    def else_(_):
        raise Exception("Validation failed")

# -------------------------------
# TestCase helper
# -------------------------------
class TestCase:
    def __init__(self, is_tx_before_valid_upper_bound: bool, is_tx_after_valid_lower_bound: bool):
        self.is_tx_before_valid_upper_bound = is_tx_before_valid_upper_bound
        self.is_tx_after_valid_lower_bound = is_tx_after_valid_lower_bound

def mock_tx(test_case: TestCase) -> Transaction:
    tx = mocktail_tx()
    tx = tx_in(invalid_hereafter, test_case.is_tx_before_valid_upper_bound, 199)
    tx = tx_out(invalid_before, test_case.is_tx_after_valid_lower_bound, 101)
    tx = complete(tx)
    return tx

# -------------------------------
# Tests
# -------------------------------
def test_md201_l6_test_success():
    datum = Datum(must_be_after=100, must_be_before=200)
    tx = mock_tx(TestCase(True, True))
    assert CheckTime.spend(datum, None, mock_utxo_ref(0, 0), tx)

def test_md201_l6_test_failed_with_invalid_before():
    datum = Datum(must_be_after=100, must_be_before=200)
    tx = mock_tx(TestCase(False, True))
    assert not CheckTime.spend(datum, None, mock_utxo_ref(0, 0), tx)

def test_md201_l6_test_failed_with_invalid_hereafter():
    datum = Datum(must_be_after=100, must_be_before=200)
    tx = mock_tx(TestCase(True, False))
    assert not CheckTime.spend(datum, None, mock_utxo_ref(0, 0), tx)
