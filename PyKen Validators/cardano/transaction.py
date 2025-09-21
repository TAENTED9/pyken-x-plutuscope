# cardano/transaction

from typing import Optional, List, Dict, Tuple
from cardano.address import Address, Credential
from cardano.assets import Value, Lovelace, PolicyId
from cardano.certificate import Certificate
from cardano.governance import ProposalProcedure, GovernanceActionId, Vote, Voter
from aiken.crypto import VerificationKeyHash, ScriptHash, Data, DataHash

Void = Data

# Datum
class Datum:
    @staticmethod
    def NoDatum():
        return {"type": "NoDatum"}

    @staticmethod
    def DatumHash(data_hash: DataHash):
        return {"type": "DatumHash", "data_hash": data_hash}

    @staticmethod
    def InlineDatum(data: Data):
        return {"type": "InlineDatum", "data": data}


# Input
class Input:
    def __init__(self, output_reference: "OutputReference", output: "Output"):
        self.output_reference = output_reference
        self.output = output


# Output
class Output:
    def __init__(
        self,
        address: Address,
        value: Value,
        datum: Datum,
        reference_script: Optional[ScriptHash]
    ):
        self.address = address
        self.value = value
        self.datum = datum
        self.reference_script = reference_script


# OutputReference
class OutputReference:
    def __init__(self, transaction_id: "TransactionId", output_index: int):
        self.transaction_id = transaction_id
        self.output_index = output_index


# Redeemer = Data (alias)
Redeemer = Data or Void


# ScriptPurpose
class ScriptPurpose:
    @staticmethod
    def Mint(policy_id: "PolicyId"):
        return {"type": "Mint", "policy_id": policy_id}

    @staticmethod
    def Spend(output_reference: OutputReference):
        return {"type": "Spend", "output_reference": output_reference}

    @staticmethod
    def Withdraw(credential: "Credential"):
        return {"type": "Withdraw", "credential": credential}

    @staticmethod
    def Publish(at: int, certificate: Certificate):
        return {"type": "Publish", "at": at, "certificate": certificate}

    @staticmethod
    def Vote(voter: Voter):
        return {"type": "Vote", "voter": voter}

    @staticmethod
    def Propose(at: int, proposal_procedure: ProposalProcedure):
        return {"type": "Propose", "at": at, "proposal_procedure": proposal_procedure}


# Transaction
class Transaction:
    def __init__(
        self,
        inputs: List[Input],
        reference_inputs: List[Input],
        outputs: List[Output],
        fee: Lovelace,
        mint: Value,
        certificates: List[Certificate],
        withdrawals: List[Tuple["Credential", Lovelace]],
        validity_range: "ValidityRange",
        extra_signatories: List["VerificationKeyHash"],
        redeemers: List[Tuple["ScriptPurpose", Data]],
        datums: Dict[DataHash, Data],
        id: "TransactionId",
        votes: List[Tuple[Voter, List[Tuple[GovernanceActionId, Vote]]]],
        proposal_procedures: List[ProposalProcedure],
        current_treasury_amount: Optional[Lovelace],
        treasury_donation: Optional[Lovelace],
    ):
        self.inputs = inputs
        self.reference_inputs = reference_inputs
        self.outputs = outputs
        self.fee = fee
        self.mint = mint
        self.certificates = certificates
        self.withdrawals = withdrawals
        self.validity_range = validity_range
        self.extra_signatories = extra_signatories
        self.redeemers = redeemers
        self.datums = datums
        self.id = id
        self.votes = votes
        self.proposal_procedures = proposal_procedures
        self.current_treasury_amount = current_treasury_amount
        self.treasury_donation = treasury_donation


# Aliases
TransactionId = str  # Hash<Blake2b_256, Transaction>
ValidityRange = Tuple[int, int]  # Interval<Int>


def placeholder(**overrides) -> Transaction:
    """
    Factory for Transaction placeholders.
    Returns a fresh Transaction with default values, 
    but any field can be overridden.
    """
    base = Transaction(
        inputs=[],
        reference_inputs=[],
        outputs=[],
        fee=0,
        mint={},   # or Value.zero if you want consistency
        certificates=[],
        withdrawals=[],
        validity_range=(0, 0),   # like interval.everything
        extra_signatories=[],
        redeemers=[],
        datums={},
        id="0" * 64,
        votes=[],
        proposal_procedures=[],
        current_treasury_amount=None,
        treasury_donation=None,
    )
    for key, val in overrides.items():
        setattr(base, key, val)
    return base



# Functions
def find_input(inputs: List[Input], output_reference: OutputReference) -> Optional[Input]:
    for i in inputs:
        if i.output_reference.transaction_id == output_reference.transaction_id and \
           i.output_reference.output_index == output_reference.output_index:
            return i
    return None


def find_datum(outputs: List[Output], datums: Dict[DataHash, Data], datum_hash: DataHash) -> Optional[Data]:
    if datum_hash in datums:
        return datums[datum_hash]
    for o in outputs:
        if isinstance(o.datum, dict) and o.datum.get("type") == "InlineDatum":
            if o.datum["data"].hash == datum_hash:
                return o.datum["data"]
    return None


def find_script_outputs(outputs: List[Output], script_hash: ScriptHash) -> List[Output]:
    return [o for o in outputs if o.reference_script == script_hash]
