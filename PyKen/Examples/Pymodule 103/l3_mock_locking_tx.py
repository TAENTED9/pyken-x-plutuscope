# l3_mock_locking_tx.py
from cardano.address import Address, Script
from cardano.assets import from_lovelace
from cardano.transaction import InlineDatum, Output, Transaction, placeholder
from mocktail import (
    add_output,
    complete,
    mock_script_address,
    mock_script_hash,
    mock_script_output,
    mocktail_tx,
    tx_out,
    tx_out_inline_datum,
)


class MockDatum:
    """Mirror of Aiken `type MockDatum { MockDatum }`"""
    pass


def mock_locking_tx() -> Transaction:
    output = Output(
        address=Address(
            payment_credential=Script(mock_script_hash(0)),
            stake_credential=None,
        ),
        value=from_lovelace(10_000_000),
        datum=InlineDatum(MockDatum()),
        reference_script=None,
    )
    return placeholder(outputs=[output])


def test_m103_l3_mocktail_mock_address():
    tx = mock_locking_tx()
    [output] = tx.outputs
    assert output.address == mock_script_address(0, None)


# --- Mocktail tx builder ---
def mock_locking_tx_mocktail_tx_builder() -> Transaction:
    tx = mocktail_tx()
    tx = tx_out(True, tx, mock_script_address(0, None), from_lovelace(10_000_000))
    tx = tx_out_inline_datum(True, tx, MockDatum())
    tx = complete(tx)
    return tx


def test_m103_l3_mocktail_tx_builder():
    tx = mock_locking_tx()
    mocktail_built = mock_locking_tx_mocktail_tx_builder()
    assert tx == mocktail_built


def mock_locking_tx_mocktail_tx() -> Transaction:
    output = mock_script_output(
        mock_script_address(0, None),
        from_lovelace(10_000_000),
        InlineDatum(MockDatum()),
    )
    tx = placeholder()
    tx = add_output(True, tx, output)
    return tx


def test_m103_l3_mocktail_tx():
    tx = mock_locking_tx()
    mocktail_built = mock_locking_tx_mocktail_tx()
    assert tx == mocktail_built
