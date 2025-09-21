# option_utils.py
# Python mirror of aiken/option utilities for PyKen

from typing import Callable, List, Optional, TypeVar, Union

T = TypeVar("T")
U = TypeVar("U")
V = TypeVar("V")


# ---------------- Inspecting ----------------

def is_none(opt: Optional[T]) -> bool:
    return opt is None


def is_some(opt: Optional[T]) -> bool:
    return opt is not None


# ---------------- Combining ----------------

def and_then(opt: Optional[T], then: Callable[[T], Optional[U]]) -> Optional[U]:
    if opt is None:
        return None
    return then(opt)


def choice(options: List[Optional[T]]) -> Optional[T]:
    for o in options:
        if o is not None:
            return o
    return None


def flatten(opt: Optional[Optional[T]]) -> Optional[T]:
    return opt if opt is None or not isinstance(opt, (list, tuple)) else opt


def map_opt(opt: Optional[T], fn: Callable[[T], U]) -> Optional[U]:
    if opt is None:
        return None
    return fn(opt)


def map2(
    opt_a: Optional[T],
    opt_b: Optional[U],
    fn: Callable[[T, U], V],
) -> Optional[V]:
    if opt_a is None or opt_b is None:
        return None
    return fn(opt_a, opt_b)


def map3(
    opt_a: Optional[T],
    opt_b: Optional[U],
    opt_c: Optional[V],
    fn: Callable[[T, U, V], T],
) -> Optional[T]:
    if opt_a is None or opt_b is None or opt_c is None:
        return None
    return fn(opt_a, opt_b, opt_c)


def or_try(opt: Optional[T], compute_default: Callable[[], Optional[T]]) -> Optional[T]:
    if opt is None:
        return compute_default()
    return opt


# ---------------- Transforming ----------------

def or_else(opt: Optional[T], default: T) -> T:
    if opt is None:
        return default
    return opt
