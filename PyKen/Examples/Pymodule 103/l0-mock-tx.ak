use cardano/assets.{PolicyId}
use cardano/transaction.{OutputReference, Transaction, placeholder}
use aiken/crypto.{Data}
use mocktail.{complete, mock_utxo_ref, mocktail_tx}
fn transaction_placeholder() -> Transaction {
  placeholder
}
validator always_succeed {
  mint(_redeemer: Data, _policy_id: PolicyId, _tx: Transaction) {
    True
  }
  spend(_datum: Option<Data>, _redeemer: Data, _input: OutputReference, _tx: Transaction) {
    True
  }
  else(_) {
    fail
  }
}
test m103_l0_aiken_builtin_placeholder {
  expect transaction_placeholder() == placeholder
}
test m103_l0_aiken_mocktail_tx {
  let tx = complete(mocktail_tx())
  expect placeholder == tx
}
test m103_l0_always_succeed_minting_policy {
  always_succeed.mint(None, "", placeholder)
}
test m103_l0_always_succeed_spending_validator {
  let OutputReference { .. } = input_ref
  always_succeed.spend(None, Void, input_ref, placeholder)
}
test m103_l0_mocktail_mock_utxo_ref {
  expect mock_utxo_ref(0, 0) == OutputReference { transaction_id: "cd82a190d3b4ef95a50bd791882959f541e308adb69b12d022d94a6d9f02bcf0", output_index: 0 }
}