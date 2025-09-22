# cardano/address.py
from dataclasses import dataclass, asdict
from typing import Optional

# --- Credentials ---
@dataclass
class VerificationKey:
    hash: str

@dataclass
class Script:
    hash: str

from typing import Union

Credential = Union[VerificationKey, Script]  # union-y in Aiken

PaymentCredential = Credential

@dataclass
class Pointer:
    slot_number: int
    transaction_index: int
    certificate_index: int

@dataclass
class Referenced:
    inline: Optional[Credential] = None
    pointer: Optional[Pointer] = None

StakeCredential = Referenced

# --- Address ---
@dataclass
class Address:
    payment_credential: PaymentCredential
    stake_credential: Optional[StakeCredential] = None

    def to_dict(self):
        return asdict(self)

# --- Smart-constructors ---
def from_script(script_hash: str) -> Address:
    return Address(payment_credential=Script(script_hash))

def from_verification_key(vk_hash: str) -> Address:
    return Address(payment_credential=VerificationKey(vk_hash))

def with_delegation_key(addr: Address, vk_hash: str) -> Address:
    addr.stake_credential = Referenced(inline=VerificationKey(vk_hash))
    return addr

def with_delegation_script(addr: Address, script_hash: str) -> Address:
    addr.stake_credential = Referenced(inline=Script(script_hash))
    return addr

# --- Mocktail helpers ---
def mock_pub_key_hash(i: int) -> str:
    return f"mock-pkh-{i}"

def mock_pub_key_address(i: int, stake=None) -> Address:
    return from_verification_key(mock_pub_key_hash(i))

def mock_pub_key_output(address: Address, value):
    # depending on your Output model (not present yet), return a tuple/dict or dataclass
    return {"address": address, "value": value}
