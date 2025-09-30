# cardano/script_context

from typing import Optional
from cardano.transaction import Transaction, OutputReference, Data, PolicyId
from cardano.certificate import Certificate, Credential
from cardano.governance import ProposalProcedure, Voter 

class ScriptInfo:
    @staticmethod
    def Minting(policy_id: PolicyId):
        return {"type": "Minting", "policy_id": policy_id}

    @staticmethod
    def Spending(output: OutputReference, datum: Optional[Data]):
        return {"type": "Spending", "output": output, "datum": datum}

    @staticmethod
    def Withdrawing(credential: "Credential"):
        return {"type": "Withdrawing", "credential": credential}

    @staticmethod
    def Publishing(at: int, certificate: Certificate):
        return {"type": "Publishing", "at": at, "certificate": certificate}

    @staticmethod
    def Voting(voter: Voter):
        return {"type": "Voting", "voter": voter}

    @staticmethod
    def Proposing(at: int, proposal_procedure: ProposalProcedure):
        return {"type": "Proposing", "at": at, "proposal_procedure": proposal_procedure}

class ScriptContext:
    def __init__(self, transaction: Transaction, redeemer: Data, info: dict):
        self.transaction = transaction
        self.redeemer = redeemer
        self.info = info


# Export Aiken-style names directly for compatibility
Minting = ScriptInfo.Minting
Spending = ScriptInfo.Spending
Withdrawing = ScriptInfo.Withdrawing
Publishing = ScriptInfo.Publishing
Voting = ScriptInfo.Voting
Proposing = ScriptInfo.Proposing
