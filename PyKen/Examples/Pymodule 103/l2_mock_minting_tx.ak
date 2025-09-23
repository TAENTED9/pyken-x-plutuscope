use cardano/assets.{from_asset}
use cardano/transaction.{placeholder, Transaction}
use mocktail.{add_mint, complete, mint, mock_policy_id, mocktail_tx}
fn mock_token_name() -> str {
  "test token name"
}
fn mock_minting_tx() -> Transaction {
  placeholder(mint=from_asset(mock_policy_id(0), mock_token_name(), 1))
}
test m103_l2_mock_minting_tx {
  let tx = mock_minting_tx()
  expect tx.mint == from_asset(mock_policy_id(0), mock_token_name(), 1)
}
fn mock_minting_tx_mocktail_tx_builder() -> Transaction {
  mocktail_tx()
  |> mint(True, 1, mock_policy_id(0), mock_token_name())
  |> complete()
}
test m103_l2_mocktail_tx_builder {
  expect mock_minting_tx() == mock_minting_tx_mocktail_tx_builder()
}
fn mock_minting_tx_mocktail_tx() -> Transaction {
  placeholder
  |> add_mint(True, from_asset(mock_policy_id(0), mock_token_name(), 1))
}
test m103_l2_mocktail_tx {
  expect mock_minting_tx() == mock_minting_tx_mocktail_tx()
}