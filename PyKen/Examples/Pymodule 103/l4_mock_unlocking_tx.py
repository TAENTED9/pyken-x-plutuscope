# l4_mock_unlocking_tx.py
from typing import Dict, List, Tuple
from cardano.address import Address, Script
from cardano.assets import from_lovelace
from cardano.transaction import (
    InlineDatum,
    Input,
    Output,
    Redeemer,
    ScriptPurpose,
    Spend,
    Transaction,
    placeholder,
)
from mocktail import (
    add_input,
    complete,
    mock_script_address,
    mock_script_hash,
    mock_script_output,
    mock_tx_hash,
    mock_utxo_ref,
    mocktail_tx,
    tx_in,
    tx_in_inline_datum,
)


# --- Dummy datatypes to mirror Aiken's custom types ---
class MockDatum:
    pass


class MockRedeemer:
    pass


# In unit tests, we seldom use this field
def get_mock_datums() -> Dict[str, MockDatum]:
    datum = MockDatum()
    # Simplified hash key; real Aiken would cbor.serialise(datum)
    return {"hash-of-MockDatum": datum}


# In unit tests, we seldom use this field
def get_mock_redeemers() -> List[Tuple[ScriptPurpose, Redeemer]]:
    redeemer = MockRedeemer()
    return [(Spend(mock_utxo_ref(0, 0)), redeemer)]


def mock_unlocking_tx() -> Transaction:
    input_item = Input(
        output_reference=mock_utxo_ref(0, 0),
        output=Output(
            address=Address(
                payment_credential=Script(mock_script_hash(0)),
                stake_credential=None,
            ),
            value=from_lovelace(10_000_000),
            datum=InlineDatum(MockDatum()),
            reference_script=None,
        ),
    )

    return placeholder(
        inputs=[input_item],
        redeemers=get_mock_redeemers(),
        datums=get_mock_datums(),
    )


# --- Mocktail tx builder ---
def mock_locking_tx_mocktail_tx_builder() -> Transaction:
    tx = mocktail_tx()
    tx = tx_in(
        True,
        tx,
        mock_tx_hash(0),
        0,
        from_lovelace(10_000_000),
        mock_script_address(0, None),
    )
    tx = tx_in_inline_datum(True, tx, MockDatum())
    tx = complete(tx)
    return tx


def test_m103_l4_mocktail_tx_builder():
    tx_inputs = mock_unlocking_tx().inputs
    mocktail_tx_inputs = mock_locking_tx_mocktail_tx_builder().inputs
    assert tx_inputs == mocktail_tx_inputs


def mock_locking_tx_mocktail_tx() -> Transaction:
    input_item = Input(
        output_reference=mock_utxo_ref(0, 0),
        output=mock_script_output(
            mock_script_address(0, None),
            from_lovelace(10_000_000),
            InlineDatum(MockDatum()),
        ),
    )
    tx = placeholder()
    tx = add_input(True, tx, input_item)
    return tx


def test_m103_l4_mocktail_tx():
    tx_inputs = mock_unlocking_tx().inputs
    mocktail_tx_inputs = mock_locking_tx_mocktail_tx().inputs
    assert tx_inputs == mocktail_tx_inputs
