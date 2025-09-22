# cocktail.py
# Python mirror of Aiken cocktail/vodka utilities for PyKen

from cardano.address import Address 
from typing import List, Optional, Tuple, Any
from cardano.transaction import Input, Output

# ---------------- Address ----------------

def compare_script_address(x: "Address", y: "Address") -> int:
    # return -1, 0, 1 like Ordering
    assert x.payment_credential[0] == "Script"
    assert y.payment_credential[0] == "Script"
    return (x.payment_credential[1] > y.payment_credential[1]) - (
        x.payment_credential[1] < y.payment_credential[1]
    )


def compare_address(x: "Address", y: "Address") -> int:
    x_hash = x.payment_credential
    y_hash = y.payment_credential
    if x_hash[0] == "Script" and y_hash[0] == "Script":
        return (x_hash[1] > y_hash[1]) - (x_hash[1] < y_hash[1])
    elif x_hash[0] == "VerificationKey" and y_hash[0] == "VerificationKey":
        return (x_hash[1] > y_hash[1]) - (x_hash[1] < y_hash[1])
    return 0  # Equal


def address_payment_key(address: "Address") -> bytes:
    cred_type, key = address.payment_credential
    return key


def address_pub_key(address: "Address") -> Optional[bytes]:
    if address.payment_credential[0] == "VerificationKey":
        return address.payment_credential[1]
    return None


def address_script_hash(address: "Address") -> Optional[bytes]:
    if address.payment_credential[0] == "Script":
        return address.payment_credential[1]
    return None


# ---------------- Converter ----------------

def convert_int_to_bytes(i: int) -> bytes:
    return str(i).encode()


def get_number_digit(i: int) -> int:
    return 10 ** (len(str(i)) - 1)


# ---------------- Extra Signatories ----------------

def key_signed(extra_signatories: List[bytes], key: bytes) -> bool:
    return key in extra_signatories


def one_of_keys_signed(extra_signatories: List[bytes], keys: List[bytes]) -> bool:
    return any(k in extra_signatories for k in keys)


def all_keys_signed(extra_signatories: List[bytes], keys: List[bytes]) -> bool:
    return all(k in extra_signatories for k in keys)


# ---------------- Inputs ----------------

def input_inline_datum(input_: "Input") -> Any:
    kind, raw_datum = input_.output.datum
    assert kind == "InlineDatum"
    return raw_datum


def only_input_datum_with(inputs: List["Input"], policy, name):
    for inp in inputs:
        if inp.output.value.get((policy, name), 0) == 1:
            return input_inline_datum(inp)
    raise Exception("No matching input")


def inputs_at(inputs: List["Input"], address: "Address") -> List["Input"]:
    return [inp for inp in inputs if inp.output.address == address]


def inputs_with(inputs: List["Input"], policy, name) -> List["Input"]:
    return [inp for inp in inputs if inp.output.value.get((policy, name), 0) == 1]


# ---------------- Outputs ----------------

def output_inline_datum(output: "Output") -> Any:
    kind, raw_datum = output.datum
    assert kind == "InlineDatum"
    return raw_datum


def outputs_at(outputs: List["Output"], address: "Address") -> List["Output"]:
    return [o for o in outputs if o.address == address]


def outputs_with(outputs: List["Output"], policy, name) -> List["Output"]:
    return [o for o in outputs if o.value.get((policy, name), 0) == 1]


# ---------------- Value ----------------

def value_length(value: dict) -> int:
    return len(value)


def get_all_value_to(outputs: List["Output"], address: "Address") -> dict:
    result = {}
    for o in outputs:
        if o.address == address:
            for k, v in o.value.items():
                result[k] = result.get(k, 0) + v
    return result


def get_all_value_from(inputs: List["Input"], address: "Address") -> dict:
    result = {}
    for i in inputs:
        if i.output.address == address:
            for k, v in i.output.value.items():
                result[k] = result.get(k, 0) + v
    return result


def value_geq(greater: dict, smaller: dict) -> bool:
    return all(greater.get(k, 0) >= v for k, v in smaller.items())


def value_tokens(value: dict) -> List[Tuple[str, str, int]]:
    return [(pid, aname, qty) for (pid, aname), qty in value.items() if pid != ""]
