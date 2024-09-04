import re
import typing as t


from pycroft.helpers.errorcode import Type1Code, Type2Code


def encode_type1_user_id(user_id: int) -> str:
    """Append a type-1 error detection code to the user_id."""
    return f"{user_id:04d}-{Type1Code.calculate(user_id):d}"


type1_user_id_pattern = re.compile(r"^(\d{4,})-(\d)$")


def decode_type1_user_id(string: str) -> tuple[str, str] | None:
    """
    If a given string is a type1 user id return a (user_id, code) tuple else
    return None.

    :param ustring: Type1 encoded user ID
    :returns: (number, code) pair or None
    """
    match = type1_user_id_pattern.match(string)
    return t.cast(tuple[str, str], match.groups()) if match else None


def encode_type2_user_id(user_id: int) -> str:
    """Append a type-2 error detection code to the user_id."""
    return f"{user_id:04d}-{Type2Code.calculate(user_id):02d}"


type2_user_id_pattern = re.compile(r"^(\d{4,})-(\d{2})$")


def decode_type2_user_id(string: str) -> tuple[str, str] | None:
    """
    If a given string is a type2 user id return a (user_id, code) tuple else
    return None.

    :param unicode string: Type2 encoded user ID
    :returns: (number, code) pair or None
    :rtype: (Integral, Integral) | None
    """
    match = type2_user_id_pattern.match(string)
    return t.cast(tuple[str, str], match.groups()) if match else None


def check_user_id(string: str) -> bool:
    """
    Check if the given string is a valid user id (type1 or type2).

    :param string: Type1 or Type2 encoded user ID
    :returns: True if user id was valid, otherwise False
    :rtype: Boolean
    """
    if not string:
        return False
    idsplit = string.split("-")
    if len(idsplit) != 2:
        return False
    uid, code = idsplit
    encode = encode_type2_user_id if len(code) == 2 else encode_type1_user_id
    return string == encode(int(uid))
