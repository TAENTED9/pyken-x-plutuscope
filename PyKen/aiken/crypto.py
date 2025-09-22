# aiken/crypto.py
from typing import Any


# === Types (aliases & placeholders) ===

# Hash algorithms (placeholders)
class Blake2b_224: pass
class Blake2b_256: pass
class Keccak_256: pass
class Sha2_256: pass
class Sha3_256: pass

# Aliases (just bytes in Python)
Hash = bytes
Data = bytes
DataHash = bytes
Script = bytes
ScriptHash = bytes
Signature = bytes
VerificationKey = bytes
VerificationKeyHash = bytes


# === Hashing Functions (stubs) ===

def blake2b_224(data: bytes) -> Hash:
    """Compute a blake2b-224 digest (stub)."""
    return b"<blake2b_224_hash>"


def blake2b_256(data: bytes) -> Hash:
    """Compute a blake2b-256 digest (stub)."""
    return b"<blake2b_256_hash>"


def keccak_256(data: bytes) -> Hash:
    """Compute a keccak-256 digest (stub)."""
    return b"<keccak_256_hash>"


def sha2_256(data: bytes) -> Hash:
    """Compute a sha2-256 digest (stub)."""
    return b"<sha2_256_hash>"


def sha3_256(data: bytes) -> Hash:
    """Compute a sha3-256 digest (stub)."""
    return b"<sha3_256_hash>"


# === Signature Verification (stubs) ===

def verify_ecdsa_signature(
    key: VerificationKey, msg: bytes, sig: Signature
) -> bool:
    """Verify an ECDSA signature (stub)."""
    return False


def verify_ed25519_signature(
    key: VerificationKey, msg: bytes, sig: Signature
) -> bool:
    """Verify an Ed25519 signature (stub)."""
    return False


def verify_schnorr_signature(
    key: VerificationKey, msg: bytes, sig: Signature
) -> bool:
    """Verify a Schnorr signature (stub)."""
    return False
