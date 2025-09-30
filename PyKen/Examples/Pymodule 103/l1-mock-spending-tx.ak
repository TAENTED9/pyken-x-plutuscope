use cardano/address.{Address, VerificationKey}
use cardano/assets.{from_asset, from_lovelace}
use cardano/transaction.{Input, Output, Transaction, placeholder, NoDatum}
use mocktail.{add_input, add_output, complete, mock_pub_key_address, mock_pub_key_hash, mock_pub_key_output, mock_tx_hash, mock_utxo_ref, mocktail_tx, set_fee, tx_in, tx_out}
fn mock_spending_tx() -> Transaction {
  let input_item = Input { output_reference: mock_utxo_ref(0, 0), output: Output { address: Address { payment_credential: VerificationKey(mock_pub_key_hash(0)), stake_credential: None }, value: from_asset("", "", 10000000), datum: NoDatum, reference_script: None } }
  let output_item = Output { address: Address { payment_credential: VerificationKey(mock_pub_key_hash(1)), stake_credential: None }, value: from_lovelace(9000000), datum: NoDatum, reference_script: None }
  placeholder(inputs=[input_item], outputs=[output_item], fee=1000000)
}
test m103_l1_mocktail_mock_address {
  let tx = mock_spending_tx()
  expect [input] = tx.inputs
  let address = input.output.address
  expect address == mock_pub_key_address(0, None)
}
test m103_l1_mocktail_mock_output {
  let tx = mock_spending_tx()
  expect [input] = tx.inputs
  expect input.output == mock_pub_key_output(mock_pub_key_address(0, None), from_lovelace(10000000))
}
test m103_l1_mocktail_mock_output_2 {
  let tx = mock_spending_tx()
  expect [output] = tx.outputs
  expect output == mock_pub_key_output(mock_pub_key_address(1, None), from_lovelace(9000000))
}
fn mock_spending_tx_mocktail_tx_builder() -> Transaction {
  mocktail_tx()
  |> tx_in(True, mock_tx_hash(0), 0, from_lovelace(10000000), mock_pub_key_address(0, None))
  |> tx_out(True, mock_pub_key_address(1, None), from_lovelace(9000000))
  |> complete()
  |> set_fee(True, 1000000)
}
test m103_l1_mocktail_tx_builder {
  let tx = mock_spending_tx()
  let mocktail_tx_result = mock_spending_tx_mocktail_tx_builder()
  expect tx == mocktail_tx_result
}
fn mock_spending_tx_mocktail_tx() -> Transaction {
  let input_item = Input { output_reference: mock_utxo_ref(0, 0), output: mock_pub_key_output(mock_pub_key_address(0, None), from_lovelace(10000000)) }
  let output_item = mock_pub_key_output(mock_pub_key_address(1, None), from_lovelace(9000000))
  placeholder
  |> add_input(True, input_item)
  |> add_output(True, output_item)
  |> set_fee(True, 1000000)
}
test m103_l1_mocktail_tx {
  let tx = mock_spending_tx()
  let mocktail_tx_result = mock_spending_tx_mocktail_tx()
  expect tx == mocktail_tx_result
}