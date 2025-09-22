# mocktail.py
"""

Combined utilities: a full-fidelity Mocktail Tx builder plus "virgin" mock helpers
(from mocktail_virgin). This single-file module attempts to import real Cardano
library types when available and falls back to lightweight Python stand-ins when not.

Exports convenience mock constructors (mock_policy_id, mock_utxo_ref, mock_pub_key_address,
mock_script_address, mock_pub_key_output, mock_script_output, mock_interval) and
an immutable-style MocktailTx builder (mocktail_tx, tx_in, tx_out, mint, complete, etc.).
"""

from dataclasses import dataclass, replace
from typing import Optional, Any, List, Tuple, Dict
import copy

try:
    from cardano.address import (
        Address, VerificationKey, Script, Referenced, StakeCredential
    )
    from cardano.transaction import (
        Transaction, Input, Output, OutputReference, Datum, InlineDatum, Redeemer, placeholder
    )
    from cardano.assets import Value, merge as assets_merge, zero as assets_zero, from_asset
    HAS_CARDANO = True
except Exception:
    HAS_CARDANO = False
    # lightweight fallbacks for environments without the cardano libs
    @dataclass
    class OutputReference:
        transaction_id: str
        output_index: int

    @dataclass
    class Output:
        address: Any
        value: Any
        datum: Optional[Any] = None
        reference_script: Optional[Any] = None

    @dataclass
    class Input:
        output_reference: OutputReference
        output: Output

    class InlineDatum:
        def __init__(self, datum):
            self.datum = datum

    # Datum fallback with NoDatum sentinel
    class Datum:
        @staticmethod
        def NoDatum():
            return None

    # Minimal Transaction fallback
    @dataclass
    class Transaction:
        inputs: List[Input] = None
        reference_inputs: List[Input] = None
        outputs: List[Output] = None
        fee: int = 0
        mint: Any = None
        certificates: List[Any] = None
        withdrawals: List[Any] = None
        validity_range: Any = None
        extra_signatories: List[Any] = None
        redeemers: List[Any] = None
        datums: Dict[Any, Any] = None
        id: str = "0" * 64
        votes: List[Any] = None
        proposal_procedures: List[Any] = None
        current_treasury_amount: Optional[int] = None
        treasury_donation: Optional[int] = None

    def placeholder(**kwargs):
        t = Transaction(
            inputs=[],
            reference_inputs=[],
            outputs=[],
            fee=0,
            mint={},
            certificates=[],
            withdrawals=[],
            validity_range=None,
            extra_signatories=[],
            redeemers=[],
            datums={},
            id="0" * 64,
            votes=[],
            proposal_procedures=[],
            current_treasury_amount=None,
            treasury_donation=None,
        )
        for k, v in kwargs.items():
            setattr(t, k, v)
        return t

    # Asset helpers fallback
    assets_merge = None
    assets_zero = {}
    def from_asset(policy: str, token_name: str, amount: int):
        # simple representation for mint values
        return { (policy, token_name): amount }

# -------------------------
# CBOR and datum hash fallbacks
# -------------------------
try:
    import aiken.cbor as cbor
    from aiken.crypto import blake2b_256
except Exception:
    class cbor:
        @staticmethod
        def serialise(obj) -> bytes:
            return repr(obj).encode("utf-8")

    def blake2b_256(data: bytes) -> bytes:
        return (b"hash:" + data)[:32]

# -------------------------
# Virgin mock helpers (from mocktail_virgin), adapted to work with fallback types
# -------------------------

# -----------------------------
# Hash mocks (string-based)
# -----------------------------
def mock_key_hash(variation: int) -> str:
    return f"mock-key-hash-{variation}"

def mock_policy_id(variation: int) -> str:
    return f"mock-policy-id-{variation}"

def mock_pub_key_hash(variation: int) -> str:
    return f"mock-pubkey-hash-{variation}"

def mock_script_hash(variation: int) -> str:
    return f"mock-script-hash-{variation}"

def mock_stake_key_hash(variation: int) -> str:
    return f"mock-stakekey-hash-{variation}"

def mock_script_stake_key_hash(variation: int) -> str:
    return f"mock-script-stakekey-hash-{variation}"

def mock_tx_hash(variation: int) -> str:
    return f"mock-tx-hash-{variation:04d}"

# -----------------------------
# Credential + Address mocks
# -----------------------------
if HAS_CARDANO:
    def mock_verification_key_credential(variation: int):
        return VerificationKey(mock_pub_key_hash(variation))

    def mock_script_credential(variation: int):
        return Script(mock_script_hash(variation))

    def mock_pub_key_address(variation: int, stake_credential: Any = None) -> Address:
        return Address(payment_credential=mock_verification_key_credential(variation),
                       stake_credential=stake_credential)

    def mock_script_address(variation: int, stake_credential: Any = None) -> Address:
        return Address(payment_credential=mock_script_credential(variation),
                       stake_credential=stake_credential)

    def mock_pub_key_stake_cred(variation: int) -> Any:
        return Referenced(inline=VerificationKey(mock_stake_key_hash(variation)))

    def mock_script_stake_cred(variation: int) -> Any:
        return Referenced(inline=Script(mock_script_stake_key_hash(variation)))
else:
    # fallback simple address / credential representations
    @dataclass
    class VerificationKey:
        key_hash: str

    @dataclass
    class Script:
        script_hash: str

    @dataclass
    class Referenced:
        inline: Any

    @dataclass
    class Address:
        payment_credential: Any
        stake_credential: Any = None

    def mock_verification_key_credential(variation: int):
        return VerificationKey(mock_pub_key_hash(variation))

    def mock_script_credential(variation: int):
        return Script(mock_script_hash(variation))

    def mock_pub_key_address(variation: int, stake_credential: Any = None) -> Address:
        return Address(payment_credential=mock_verification_key_credential(variation),
                       stake_credential=stake_credential)

    def mock_script_address(variation: int, stake_credential: Any = None) -> Address:
        return Address(payment_credential=mock_script_credential(variation),
                       stake_credential=stake_credential)

    def mock_pub_key_stake_cred(variation: int) -> Referenced:
        return Referenced(inline=VerificationKey(mock_stake_key_hash(variation)))

    def mock_script_stake_cred(variation: int) -> Referenced:
        return Referenced(inline=Script(mock_script_stake_key_hash(variation)))

# -----------------------------
# TxRef mocks
# -----------------------------
def mock_utxo_ref(tx_variation: int, output_index: int) -> OutputReference:
    return OutputReference(transaction_id=mock_tx_hash(tx_variation), output_index=output_index)

# -----------------------------
# Output mocks
# -----------------------------
if HAS_CARDANO:
    def mock_output(address: Address, value: Value, datum: Datum, reference_script=None) -> Output:
        return Output(address=address, value=value, datum=datum, reference_script=reference_script)

    def mock_pub_key_output(address: Address, value: Value) -> Output:
        return mock_output(address, value, Datum.NoDatum(), None)

    def mock_script_output(address: Address, value: Value, datum: Datum) -> Output:
        return mock_output(address, value, datum, None)
else:
    def mock_output(address: Address, value: Any, datum: Any, reference_script=None) -> Output:
        return Output(address=address, value=value, datum=datum, reference_script=reference_script)

    def mock_pub_key_output(address: Address, value: Any) -> Output:
        return mock_output(address, value, Datum.NoDatum(), None)

    def mock_script_output(address: Address, value: Any, datum: Any) -> Output:
        return mock_output(address, value, datum, None)

# -----------------------------
# Interval mocks
# -----------------------------
def mock_interval(lower: int = None, upper: int = None):
    return (lower, upper)

# -------------------------
# Utility immutability helpers (from original mocktail)
# -------------------------
Pair = Tuple[Any, Any]

def _copy_tx(tx: Transaction) -> Transaction:
    return copy.deepcopy(tx)

def _push_list(lst: Optional[List], item):
    if lst is None:
        lst = []
    new = list(lst)
    new.append(item)
    return new

# -------------------------
# MocktailTx builder type
# -------------------------
@dataclass
class MocktailTx:
    tx: Transaction
    queue_input: Optional[Input] = None
    queue_output: Optional[Output] = None
    queue_ref_input: Optional[Input] = None

# -------------------------
# MocktailTx API (adapted)
# -------------------------

def mocktail_tx() -> MocktailTx:
    """Initialize a new MocktailTx with a fresh placeholder transaction."""
    return MocktailTx(tx=placeholder(), queue_input=None, queue_output=None, queue_ref_input=None)

# tx_in: queue or add input
def tx_in(condition: bool, mtx: MocktailTx, tx_hash: str, tx_index: int, amount, address) -> MocktailTx:
    if not condition:
        return mtx
    ref = OutputReference(transaction_id=tx_hash, output_index=tx_index)
    out = mock_pub_key_output(address, amount)
    new_input = Input(output_reference=ref, output=out)
    if mtx.queue_input is None:
        return MocktailTx(tx=mtx.tx, queue_input=new_input, queue_output=mtx.queue_output, queue_ref_input=mtx.queue_ref_input)
    else:
        new_tx = add_input(_copy_tx(mtx.tx), True, mtx.queue_input)
        return MocktailTx(tx=new_tx, queue_input=new_input, queue_output=mtx.queue_output, queue_ref_input=mtx.queue_ref_input)

def tx_in_inline_datum(condition: bool, mtx: MocktailTx, datum) -> MocktailTx:
    if not condition:
        return mtx
    if mtx.queue_input is not None:
        q = mtx.queue_input
        out = q.output
        out_with_datum = Output(address=out.address, value=out.value, datum=InlineDatum(datum), reference_script=out.reference_script)
        new_q = Input(output_reference=q.output_reference, output=out_with_datum)
        return MocktailTx(tx=mtx.tx, queue_input=new_q, queue_output=mtx.queue_output, queue_ref_input=mtx.queue_ref_input)
    else:
        out = mock_script_output(mock_script_address(0, None), assets_zero if 'assets_zero' in globals() else {}, InlineDatum(datum))
        default_input = Input(output_reference=mock_utxo_ref(0, 0), output=out)
        return MocktailTx(tx=mtx.tx, queue_input=default_input, queue_output=mtx.queue_output, queue_ref_input=mtx.queue_ref_input)

def tx_out(condition: bool, mtx: MocktailTx, address, amount) -> MocktailTx:
    if not condition:
        return mtx
    new_output = mock_pub_key_output(address, amount)
    if mtx.queue_output is None:
        return MocktailTx(tx=mtx.tx, queue_input=mtx.queue_input, queue_output=new_output, queue_ref_input=mtx.queue_ref_input)
    else:
        new_tx = add_output(_copy_tx(mtx.tx), True, mtx.queue_output)
        return MocktailTx(tx=new_tx, queue_input=mtx.queue_input, queue_output=new_output, queue_ref_input=mtx.queue_ref_input)

def tx_out_inline_datum(condition: bool, mtx: MocktailTx, datum) -> MocktailTx:
    if not condition:
        return mtx
    if mtx.queue_output is not None:
        out = mtx.queue_output
        out_with_datum = Output(address=out.address, value=out.value, datum=InlineDatum(datum), reference_script=out.reference_script)
        return MocktailTx(tx=mtx.tx, queue_input=mtx.queue_input, queue_output=out_with_datum, queue_ref_input=mtx.queue_ref_input)
    else:
        out = mock_script_output(mock_script_address(0, None), assets_zero if 'assets_zero' in globals() else {}, InlineDatum(datum))
        return MocktailTx(tx=mtx.tx, queue_input=mtx.queue_input, queue_output=out, queue_ref_input=mtx.queue_ref_input)

def mint(condition: bool, mtx: MocktailTx, quantity: int, policy_id: str, token_name: str) -> MocktailTx:
    if not condition:
        return mtx
    value = from_asset(policy_id, token_name, quantity)
    new_tx = add_mint(_copy_tx(mtx.tx), True, value)
    return MocktailTx(tx=new_tx, queue_input=mtx.queue_input, queue_output=mtx.queue_output, queue_ref_input=mtx.queue_ref_input)

def ref_tx_in(condition: bool, mtx: MocktailTx, tx_hash: str, tx_index: int, amount, address) -> MocktailTx:
    if not condition:
        return mtx
    ref = OutputReference(transaction_id=tx_hash, output_index=tx_index)
    out = mock_pub_key_output(address, amount)
    new_input = Input(output_reference=ref, output=out)
    if mtx.queue_ref_input is None:
        return MocktailTx(tx=mtx.tx, queue_input=mtx.queue_input, queue_output=mtx.queue_output, queue_ref_input=new_input)
    else:
        new_tx = add_reference_input(_copy_tx(mtx.tx), True, mtx.queue_ref_input)
        return MocktailTx(tx=new_tx, queue_input=mtx.queue_input, queue_output=mtx.queue_output, queue_ref_input=new_input)

def ref_tx_in_inline_datum(condition: bool, mtx: MocktailTx, datum) -> MocktailTx:
    if not condition:
        return mtx
    if mtx.queue_ref_input is not None:
        q = mtx.queue_ref_input
        out = q.output
        out_with_datum = Output(address=out.address, value=out.value, datum=InlineDatum(datum), reference_script=out.reference_script)
        new_q = Input(output_reference=q.output_reference, output=out_with_datum)
        return MocktailTx(tx=mtx.tx, queue_input=mtx.queue_input, queue_output=mtx.queue_output, queue_ref_input=new_q)
    else:
        out = mock_script_output(mock_script_address(0, None), assets_zero if 'assets_zero' in globals() else {}, InlineDatum(datum))
        default_input = Input(output_reference=mock_utxo_ref(0, 0), output=out)
        return MocktailTx(tx=mtx.tx, queue_input=mtx.queue_input, queue_output=mtx.queue_output, queue_ref_input=default_input)

def invalid_before(mtx: MocktailTx, condition: bool, time: int) -> MocktailTx:
    if not condition:
        return mtx
    tx = _copy_tx(mtx.tx)
    upper = None
    if getattr(tx, "validity_range", None):
        lb, ub = tx.validity_range
        upper = ub
    tx.validity_range = mock_interval(time, upper)
    return MocktailTx(tx=tx, queue_input=mtx.queue_input, queue_output=mtx.queue_output, queue_ref_input=mtx.queue_ref_input)

def invalid_hereafter(mtx: MocktailTx, condition: bool, time: int) -> MocktailTx:
    if not condition:
        return mtx
    tx = _copy_tx(mtx.tx)
    lower = None
    if getattr(tx, "validity_range", None):
        lb, ub = tx.validity_range
        lower = lb
    tx.validity_range = mock_interval(lower, time)
    return MocktailTx(tx=tx, queue_input=mtx.queue_input, queue_output=mtx.queue_output, queue_ref_input=mtx.queue_ref_input)

def required_signer_hash(mtx: MocktailTx, condition: bool, key: str) -> MocktailTx:
    if not condition:
        return mtx
    tx = _copy_tx(mtx.tx)
    tx = add_extra_signatory(tx, True, key)
    return MocktailTx(tx=tx, queue_input=mtx.queue_input, queue_output=mtx.queue_output, queue_ref_input=mtx.queue_ref_input)

def script_withdrawal(mtx: MocktailTx, condition: bool, script_hash: str, withdrawal_amount: int) -> MocktailTx:
    if not condition:
        return mtx
    tx = _copy_tx(mtx.tx)
    return MocktailTx(tx=add_withdrawal(tx, True, (("Script", script_hash), withdrawal_amount)), queue_input=mtx.queue_input, queue_output=mtx.queue_output, queue_ref_input=mtx.queue_ref_input)

# complete: flush queued items into tx and return Transaction
def complete(mtx: MocktailTx) -> Transaction:
    tx = _copy_tx(mtx.tx)
    if mtx.queue_input is not None:
        tx = add_input(tx, True, mtx.queue_input)
    if mtx.queue_output is not None:
        tx = add_output(tx, True, mtx.queue_output)
    if mtx.queue_ref_input is not None:
        tx = add_reference_input(tx, True, mtx.queue_ref_input)
    return tx

# -------------------------
# Pure transaction manipulators (return NEW Transaction)
# -------------------------

def add_input(tx: Transaction, condition: bool, input_item: Input) -> Transaction:
    if not condition:
        return tx
    new_tx = _copy_tx(tx)
    new_tx.inputs = _push_list(getattr(new_tx, "inputs", []), input_item)
    return new_tx

def add_reference_input(tx: Transaction, condition: bool, input_item: Input) -> Transaction:
    if not condition:
        return tx
    new_tx = _copy_tx(tx)
    new_tx.reference_inputs = _push_list(getattr(new_tx, "reference_inputs", []), input_item)
    return new_tx

def add_output(tx: Transaction, condition: bool, output_item: Output) -> Transaction:
    if not condition:
        return tx
    new_tx = _copy_tx(tx)
    new_tx.outputs = _push_list(getattr(new_tx, "outputs", []), output_item)
    return new_tx

def set_fee(tx: Transaction, condition: bool, lovelace_fee: int) -> Transaction:
    if not condition:
        return tx
    new_tx = _copy_tx(tx)
    new_tx.fee = lovelace_fee
    return new_tx

def add_mint(tx: Transaction, condition: bool, mint_value) -> Transaction:
    if not condition:
        return tx
    new_tx = _copy_tx(tx)
    if assets_merge is not None:
        new_tx.mint = assets_merge(getattr(new_tx, "mint", {}), mint_value)
    else:
        cur = getattr(new_tx, "mint", {}) or {}
        merged = dict(cur)
        if isinstance(mint_value, dict):
            for k, v in mint_value.items():
                merged[k] = merged.get(k, 0) + v
        new_tx.mint = merged
    return new_tx

def add_certificate(tx: Transaction, condition: bool, certificate) -> Transaction:
    if not condition:
        return tx
    new_tx = _copy_tx(tx)
    new_tx.certificates = _push_list(getattr(new_tx, "certificates", []), certificate)
    return new_tx

def add_withdrawal(tx: Transaction, condition: bool, withdrawal) -> Transaction:
    if not condition:
        return tx
    new_tx = _copy_tx(tx)
    new_tx.withdrawals = _push_list(getattr(new_tx, "withdrawals", []), withdrawal)
    return new_tx

def add_extra_signatory(tx: Transaction, condition: bool, signatory) -> Transaction:
    if not condition:
        return tx
    new_tx = _copy_tx(tx)
    new_tx.extra_signatories = _push_list(getattr(new_tx, "extra_signatories", []), signatory)
    return new_tx

def add_redeemer(tx: Transaction, condition: bool, redeemer_pair: Pair) -> Transaction:
    if not condition:
        return tx
    new_tx = _copy_tx(tx)
    new_tx.redeemers = _push_list(getattr(new_tx, "redeemers", []), redeemer_pair)
    return new_tx

def add_datum(tx: Transaction, condition: bool, datum) -> Transaction:
    if not condition:
        return tx
    new_tx = _copy_tx(tx)
    datum_bytes = cbor.serialise(datum)
    datum_hash = blake2b_256(datum_bytes)
    d = dict(getattr(new_tx, "datums", {}) or {})
    d[datum_hash] = datum
    new_tx.datums = d
    return new_tx

def set_transaction_id(tx: Transaction, condition: bool, transaction_id: str) -> Transaction:
    if not condition:
        return tx
    new_tx = _copy_tx(tx)
    new_tx.id = transaction_id
    return new_tx

# -------------------------
# Convenience re-exports
# -------------------------
mock_verfication_key_credential = mock_verification_key_credential
mock_pub_key_address = mock_pub_key_address
mock_script_credential = mock_script_credential
mock_script_address = mock_script_address
mock_key_hash = mock_key_hash
mock_policy_id = mock_policy_id
mock_pub_key_hash = mock_pub_key_hash
mock_script_hash = mock_script_hash
mock_stake_key_hash = mock_stake_key_hash
mock_script_stake_key_hash = mock_script_stake_key_hash
mock_tx_hash = mock_tx_hash
mock_utxo_ref = mock_utxo_ref
mock_output = mock_output
mock_pub_key_output = mock_pub_key_output
mock_script_output = mock_script_output
mock_interval = mock_interval

__all__ = [
    "MocktailTx",
    "mocktail_tx", "tx_in", "tx_in_inline_datum", "tx_out", "tx_out_inline_datum",
    "mint", "ref_tx_in", "ref_tx_in_inline_datum", "invalid_before", "invalid_hereafter",
    "required_signer_hash", "script_withdrawal", "complete",
    "add_input", "add_reference_input", "add_output", "set_fee", "add_mint",
    "add_certificate", "add_withdrawal", "add_extra_signatory", "add_redeemer",
    "add_datum", "set_transaction_id",
    # convenience
    "mock_pub_key_address", "mock_script_address", "mock_policy_id", "mock_pub_key_hash",
    "mock_script_hash", "mock_tx_hash", "mock_utxo_ref",
    "mock_pub_key_output", "mock_script_output",
    "mock_interval",
]
