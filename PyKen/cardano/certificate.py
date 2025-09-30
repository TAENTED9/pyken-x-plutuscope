#certificate.py
from dataclasses import dataclass, asdict
from typing import Optional, Union, Dict, Any


# ---- simple aliases for external/complex types ----
# In real app, replace these with real structures.
StakePoolId = str  # Hash<Blake2b_224, VerificationKey> (hex string)
VerificationKeyHash = str  # hex string
Credential = Dict[str, Any]  # placeholder: e.g. {"type": "KeyHash", "hash": "..."}
Lovelace = int
Never = None  # In Aiken the Option<Lovelace> becomes `Never` (always None)


# ---- Certificate variants as dataclasses ----
@dataclass
class RegisterCredential:
	credential: Credential
	deposit: Optional[Any]  # always None in current Aiken host behavior


@dataclass
class UnregisterCredential:
	credential: Credential
	refund: Optional[Any]  # always None


@dataclass
class DelegateCredential:
	credential: Credential
	delegate: "Delegate"  # forward ref


@dataclass
class RegisterAndDelegateCredential:
	credential: Credential
	delegate: "Delegate"
	deposit: Lovelace


@dataclass
class RegisterDelegateRepresentative:
	delegate_representative: Credential
	deposit: Lovelace


@dataclass
class UpdateDelegateRepresentative:
	delegate_representative: Credential


@dataclass
class UnregisterDelegateRepresentative:
	delegate_representative: Credential
	refund: Lovelace


@dataclass
class RegisterStakePool:
	stake_pool: StakePoolId
	vrf: VerificationKeyHash


@dataclass
class RetireStakePool:
	stake_pool: StakePoolId
	at_epoch: int


@dataclass
class AuthorizeConstitutionalCommitteeProxy:
	constitutional_committee_member: Credential
	proxy: Credential


@dataclass
class RetireFromConstitutionalCommittee:
	constitutional_committee_member: Credential


# Union type for Certificate
Certificate = Union[
	RegisterCredential,
	UnregisterCredential,
	DelegateCredential,
	RegisterAndDelegateCredential,
	RegisterDelegateRepresentative,
	UpdateDelegateRepresentative,
	UnregisterDelegateRepresentative,
	RegisterStakePool,
	RetireStakePool,
	AuthorizeConstitutionalCommitteeProxy,
	RetireFromConstitutionalCommittee,
]


# ---- Delegate variants ----
@dataclass
class DelegateBlockProduction:
	stake_pool: StakePoolId


@dataclass
class DelegateVote:
	delegate_representative: Credential


@dataclass
class DelegateBoth:
	stake_pool: StakePoolId
	delegate_representative: Credential


Delegate = Union[DelegateBlockProduction, DelegateVote, DelegateBoth]


# Utility to convert a dataclass variant into a tagged dict (variant name -> fields)
def dataclass_to_tagged_dict(obj) -> Dict[str, Dict]:
	return {obj.__class__.__name__: asdict(obj)}


# Example with dataclasses
if __name__ == "__main__":
	cred = {"type": "KeyHash", "hash": "abc123"}
	stake_pool_id = "stakepoolhashdeadbeef"
	vrf_hash = "vrfhashcafebabe"


	cert = RegisterStakePool(stake_pool=stake_pool_id, vrf=vrf_hash)
	print(dataclass_to_tagged_dict(cert))

