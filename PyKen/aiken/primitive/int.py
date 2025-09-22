# int_utils.py
# Python mirror of aiken/int utilities for PyKen

from typing import Optional


# ---------------- Combining ----------------

def compare(left: int, right: int) -> int:
    """
    Compare two integers.
    Returns:
      -1 if left < right
       0 if equal
       1 if left > right
    """
    if left < right:
        return -1
    elif left > right:
        return 1
    return 0


# ---------------- Transforming ----------------

def from_bytearray_big_endian(b: bytes) -> int:
    """Interpret a big-endian bytearray as an int."""
    return int.from_bytes(b, "big", signed=False)


def from_bytearray_little_endian(b: bytes) -> int:
    """Interpret a little-endian bytearray as an int."""
    return int.from_bytes(b, "little", signed=False)


def from_utf8(b: bytes) -> Optional[int]:
    """
    Parse an int from a UTF-8 encoded bytearray.
    Returns None if not a valid integer string.
    """
    try:
        s = b.decode("utf-8")
    except UnicodeDecodeError:
        return None

    # Strict check: only optional '-' followed by digits
    if not s or (s[0] == "-" and not s[1:].isdigit()) or (s[0] != "-" and not s.isdigit()):
        return None

    try:
        return int(s)
    except ValueError:
        return None


def to_string(n: int) -> str:
    """Convert an int to its string representation."""
    return str(n)
