# aiken/cbor.py

from typing import Any, Optional


class Data:
    """Placeholder for any Aiken 'Data' type"""
    def __init__(self, value: Any):
        self.value = value


def diagnostic(data: Data) -> str:
    """
    Return a human-readable CBOR diagnostic string.
    In Aiken, this is only for debugging and should not be used in production.
    """
    return f"<diagnostic:{repr(data.value)}>"


def deserialise(bytes_: bytes) -> Optional[Data]:
    """
    Reverse of serialise. Converts CBOR bytes back to Data.
    (Here it's just a stub returning None for now.)
    """
    return None


def serialise(data: Data) -> bytes:
    """
    Serialise any Data into bytes (CBOR encoding).
    Stub version: returns empty bytes.
    """
    return b""
