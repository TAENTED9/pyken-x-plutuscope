# bytearray.py
# Python mirror of aiken/bytearray utilities for PyKen

from typing import Optional, Tuple, Callable


Byte = int  # In Aiken: type alias for Int


# ---------------- Constructing ----------------

def from_int_big_endian(value: int, size: int) -> bytes:
    b = value.to_bytes(size, "big", signed=False)
    if int.from_bytes(b, "big") != value:
        raise ValueError("Value cannot fit in given size")
    return b


def from_int_little_endian(value: int, size: int) -> bytes:
    b = value.to_bytes(size, "little", signed=False)
    if int.from_bytes(b, "little") != value:
        raise ValueError("Value cannot fit in given size")
    return b


def from_string(s: str) -> bytes:
    return s.encode("utf-8")


def push(arr: bytes, byte: int) -> bytes:
    return bytes([byte % 256]) + arr


# ---------------- Inspecting ----------------

def at(arr: bytes, index: int) -> int:
    return arr[index]


def index_of(arr: bytes, sub: bytes) -> Optional[Tuple[int, int]]:
    ix = arr.find(sub)
    if ix == -1:
        return None
    return (ix, ix + len(sub) - 1)


def is_empty(arr: bytes) -> bool:
    return len(arr) == 0


def length(arr: bytes) -> int:
    return len(arr)


def test_bit(arr: bytes, ix: int) -> bool:
    byte_ix, bit_ix = divmod(ix, 8)
    if byte_ix >= len(arr):
        return False
    return (arr[byte_ix] & (1 << (7 - bit_ix))) != 0


# ---------------- Modifying ----------------

def drop(arr: bytes, n: int) -> bytes:
    return arr[n:]


def slice(arr: bytes, start: int, end: int) -> bytes:
    return arr[start:end + 1]


def take(arr: bytes, n: int) -> bytes:
    return arr[:n]


# ---------------- Combining ----------------

def concat(left: bytes, right: bytes) -> bytes:
    return left + right


def compare(left: bytes, right: bytes) -> int:
    if left < right:
        return -1
    elif left == right:
        return 0
    return 1


# ---------------- Transforming ----------------

def foldl(arr: bytes, zero, with_fn: Callable[[int, any], any]):
    acc = zero
    for b in arr:
        acc = with_fn(b, acc)
    return acc


def foldr(arr: bytes, zero, with_fn: Callable[[int, any], any]):
    acc = zero
    for b in reversed(arr):
        acc = with_fn(b, acc)
    return acc


def reduce(arr: bytes, zero, with_fn: Callable[[any, int], any]):
    acc = zero
    for b in arr:
        acc = with_fn(acc, b)
    return acc


def to_int_big_endian(arr: bytes) -> int:
    return int.from_bytes(arr, "big")


def to_int_little_endian(arr: bytes) -> int:
    return int.from_bytes(arr, "little")


def to_string(arr: bytes) -> str:
    return arr.decode("utf-8")


def to_hex(arr: bytes) -> str:
    return arr.hex()


def starts_with(arr: bytes, prefix: bytes) -> bool:
    return arr.startswith(prefix)
