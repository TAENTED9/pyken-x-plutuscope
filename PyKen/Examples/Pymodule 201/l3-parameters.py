# l3_parameters.py
from cardano.assets import PolicyId, from_lovelace
from cardano.transaction import Input, OutputReference, Transaction
from mocktail import (
    complete,
    mock_policy_id,
    mock_pub_key_address,
    mock_tx_hash,
    mock_utxo_ref,
    mocktail_tx,
    tx_in,
)

# -------------------------------
# Validator
# -------------------------------
class AlwaysSucceed:
    def __init__(self, utxo: OutputReference):
        self.utxo = utxo

    def mint(self, _redeemer, _policy_id: PolicyId, tx: Transaction) -> bool:
        return any(inp.output_reference == self.utxo for inp in tx.inputs)

    @staticmethod
    def else_(_):
        raise Exception("Validation failed")

# -------------------------------
# Test
# -------------------------------
def test_md201_l3_test_one_time_minting_policy():
    tx = (
        mocktail_tx()
        .pipe(tx_in, True, mock_tx_hash(2), 0, from_lovelace(1_000_000), mock_pub_key_address(0, None))
        .pipe(complete)
    )
    validator = AlwaysSucceed(mock_utxo_ref(2, 0))
    assert validator.mint(None, mock_policy_id(0), tx)
