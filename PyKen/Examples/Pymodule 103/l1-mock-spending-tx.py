# validators/l1_mock_spending_tx.py

from cardano.address import Address, VerificationKey
from cardano.assets import from_asset, from_lovelace
from cardano.transaction import Input, Output, Transaction, placeholder, NoDatum
from mocktail import (
    add_input, add_output, complete,
    mock_pub_key_address, mock_pub_key_hash,
    mock_pub_key_output, mock_tx_hash, mock_utxo_ref,
    mocktail_tx, set_fee, tx_in, tx_out,
)


# === Mock Spending Tx (direct record construction) ===
def mock_spending_tx() -> Transaction:
    input_item = Input(
        output_reference=mock_utxo_ref(0, 0),
        output=Output(
            address=Address(
                payment_credential=VerificationKey(mock_pub_key_hash(0)),
                stake_credential=None,
            ),
            value=from_asset("", b"", 10_000_000),
            datum=NoDatum(),
            reference_script=None,
        ),
    )

    output_item = Output(
        address=Address(
            payment_credential=VerificationKey(mock_pub_key_hash(1)),
            stake_credential=None,
        ),
        value=from_lovelace(9_000_000),
        datum=NoDatum(),
        reference_script=None,
    )

    return placeholder(
        inputs=[input_item],
        outputs=[output_item],
        fee=1_000_000,
    )


# === Tests ===
def test_m103_l1_mocktail_mock_address():
    tx = mock_spending_tx()
    input_item = tx.inputs[0]
    address = input_item.output.address
    assert address == mock_pub_key_address(0, None)


def test_m103_l1_mocktail_mock_output():
    tx = mock_spending_tx()
    input_item = tx.inputs[0]
    assert input_item.output == mock_pub_key_output(
        mock_pub_key_address(0, None),
        from_lovelace(10_000_000),
    )


def test_m103_l1_mocktail_mock_output_2():
    tx = mock_spending_tx()
    output_item = tx.outputs[0]
    assert output_item == mock_pub_key_output(
        mock_pub_key_address(1, None),
        from_lovelace(9_000_000),
    )


# === Mocktail tx builder ===
def mock_spending_tx_mocktail_tx_builder() -> Transaction:
    tx = mocktail_tx()
    tx = tx_in(True, tx, mock_tx_hash(0), 0, from_lovelace(10_000_000), mock_pub_key_address(0, None))
    tx = tx_out(True, tx, mock_pub_key_address(1, None), from_lovelace(9_000_000))
    tx = complete(tx)
    tx = set_fee(True, tx, 1_000_000)
    return tx


def test_m103_l1_mocktail_tx_builder():
    tx = mock_spending_tx()
    mocktail_tx_result = mock_spending_tx_mocktail_tx_builder()
    assert tx == mocktail_tx_result


# === Alternative Mocktail style ===
def mock_spending_tx_mocktail_tx() -> Transaction:
    input_item = Input(
        output_reference=mock_utxo_ref(0, 0),
        output=mock_pub_key_output(
            mock_pub_key_address(0, None),
            from_lovelace(10_000_000),
        ),
    )
    output_item = mock_pub_key_output(
        mock_pub_key_address(1, None),
        from_lovelace(9_000_000),
    )

    tx = placeholder()
    tx = add_input(True, input_item)
    tx = add_output(True, output_item)
    tx = set_fee(True, 1_000_000)
    return tx


def test_m103_l1_mocktail_tx():
    tx = mock_spending_tx()
    mocktail_tx_result = mock_spending_tx_mocktail_tx()
    assert tx == mocktail_tx_result
