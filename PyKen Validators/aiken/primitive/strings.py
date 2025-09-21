# string.py
# Python mirror of aiken/string utilities for PyKen

from typing import List


# ---------------- Constructing ----------------

def from_bytearray(b: bytes) -> str:
    """
    Convert a ByteArray into a String.
    Raises UnicodeDecodeError if not valid UTF-8.
    """
    return b.decode("utf-8")


def from_int(n: int) -> str:
    """
    Convert an Int to its String representation.
    """
    return str(n)


# ---------------- Combining ----------------

def concat(left: str, right: str) -> str:
    """
    Combine two Strings together.
    """
    return left + right


def join(strings: List[str], delimiter: str) -> str:
    """
    Join a list of strings with a delimiter.
    """
    return delimiter.join(strings)


# ---------------- Transforming ----------------

def to_bytearray(s: str) -> bytes:
    """
    Convert a String into a ByteArray (UTF-8 encoded).
    """
    return s.encode("utf-8")
