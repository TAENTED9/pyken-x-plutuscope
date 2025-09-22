# governance.py
from dataclasses import dataclass, asdict
from typing import Optional, List, Tuple, Dict, Union

# --- Base Aliases ---
Lovelace = int
Credential = Dict[str, str]        # Example: {"type": "KeyHash", "hash": "..."}
ScriptHash = str
VerificationKeyHash = str
TransactionId = str                # Hex string for Hash<Blake2b_256, ByteArray>
Index = int
Rational = Tuple[int, int]         # (numerator, denominator)
Mandate = int                      # epoch number (expiry)
ProtocolParametersUpdate = Dict[str, Optional[Union[int, str]]]


# ---------------- GovernanceActionId ----------------
@dataclass
class GovernanceActionId:
    transaction: TransactionId
    proposal_procedure: Index


# ---------------- ProtocolVersion ----------------
@dataclass
class ProtocolVersion:
    major: int
    minor: int


# ---------------- Constitution ----------------
@dataclass
class Constitution:
    guardrails: Optional[ScriptHash]


# ---------------- ProposalProcedure ----------------
@dataclass
class ProposalProcedure:
    deposit: Lovelace
    return_address: Credential
    governance_action: "GovernanceAction"


# ---------------- GovernanceAction (variants grouped) ----------------
class GovernanceAction:

    @dataclass
    class ProtocolParameters:
        ancestor: Optional[GovernanceActionId]
        new_parameters: ProtocolParametersUpdate
        guardrails: Optional[ScriptHash]

    @dataclass
    class HardFork:
        ancestor: Optional[GovernanceActionId]
        new_version: ProtocolVersion

    @dataclass
    class TreasuryWithdrawal:
        beneficiaries: List[Tuple[Credential, Lovelace]]
        guardrails: Optional[ScriptHash]

    @dataclass
    class NoConfidence:
        ancestor: Optional[GovernanceActionId]

    @dataclass
    class ConstitutionalCommittee:
        ancestor: Optional[GovernanceActionId]
        evicted_members: List[Credential]
        added_members: List[Tuple[Credential, Mandate]]
        quorum: Rational

    @dataclass
    class NewConstitution:
        ancestor: Optional[GovernanceActionId]
        constitution: Constitution

    @dataclass
    class NicePoll:
        pass


# ---------------- Vote Enum ----------------
class Vote:
    No = "No"
    Yes = "Yes"
    Abstain = "Abstain"


# ---------------- Voter ----------------
class Voter:

    @dataclass
    class ConstitutionalCommitteeMember:
        credential: Credential

    @dataclass
    class DelegateRepresentative:
        credential: Credential

    @dataclass
    class StakePool:
        vkey_hash: VerificationKeyHash


# ---------------- Example Usage ----------------
if __name__ == "__main__":
    # Example: Proposing a new constitution
    cred = {"type": "KeyHash", "hash": "abc123"}
    constitution = Constitution(guardrails="script123")

    action = GovernanceAction.NewConstitution(
        ancestor=None,
        constitution=constitution
    )

    proposal = ProposalProcedure(
        deposit=2_000_000,
        return_address=cred,
        governance_action=action
    )

    import json
    print(json.dumps(asdict(proposal), indent=2))
