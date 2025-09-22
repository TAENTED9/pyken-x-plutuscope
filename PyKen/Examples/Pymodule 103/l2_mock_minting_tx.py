# l2_mock_minting_tx.py
from cardano.assets import from_asset
from cardano.transaction import placeholder, Transaction
from mocktail import add_mint, complete, mint, mock_policy_id, mocktail_tx


def mock_token_name() -> str:
    return "test token name"


def mock_minting_tx() -> Transaction:
    return placeholder(
        mint=from_asset(mock_policy_id(0), mock_token_name(), 1),
    )


def test_m103_l2_mock_minting_tx():
    tx = mock_minting_tx()
    assert tx.mint == from_asset(mock_policy_id(0), mock_token_name(), 1)


# --- Mocktail tx builder ---
def mock_minting_tx_mocktail_tx_builder() -> Transaction:
    tx = mocktail_tx()
    tx = mint(True, tx, 1, mock_policy_id(0), mock_token_name())
    tx = complete(tx)
    return tx


def test_m103_l2_mocktail_tx_builder():
    assert mock_minting_tx() == mock_minting_tx_mocktail_tx_builder()


def mock_minting_tx_mocktail_tx() -> Transaction:
    tx = placeholder()
    tx = add_mint(True, tx, from_asset(mock_policy_id(0), mock_token_name(), 1))
    return tx


def test_m103_l2_mocktail_tx():
    assert mock_minting_tx() == mock_minting_tx_mocktail_tx()
