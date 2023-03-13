#  Copyright (c) 2023. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details

import typing as t
from functools import wraps

TOne = t.TypeVar("TOne")
TOther = t.TypeVar("TOther")


def extract_type(
    elements: t.Iterable[TOne | TOther], type_: type[TOne]
) -> tuple[list[TOne], list[TOther]]:
    """Extracts all elements of a certain type from an iterable.

    Does not support unions!

    :param elements: The iterable to extract from
    :param type_: The type instance of which to extract to a separate list
    :return: A tuple ``(elements of specified type, other elements)``.

    >>> extract_type([1, 2, 3, "a", "b", "c"], int)
    ([1, 2, 3], ['a', 'b', 'c'])
    """
    of_type_one = []
    other = []
    for elem in elements:
        match elem:
            case type_():
                of_type_one.append(elem)
            case _:
                other.append(elem)
    return of_type_one, other


TException = t.TypeVar("TException", bound=Exception)
TRet = t.TypeVar("TRet")
P = t.ParamSpec("P")


def with_catch(
    f: t.Callable[P, TRet], exc_type: type[TException]
) -> t.Callable[P, TRet | TException]:
    """Wraps a function to catch a specific exception and return it instead of raising it.

    >>> l = ["1", "2", "a", "3"]
    >>> [with_catch(int, ValueError)(x) for x in l]
    [1, 2, ValueError("invalid literal for int() with base 10: 'a'"), 3]
    """

    @wraps(f)
    def _f(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except exc_type as e:
            return e

    return _f
