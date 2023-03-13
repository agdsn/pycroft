#  Copyright (c) 2023. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details

import typing as t
from functools import wraps

# OVERLOADS
TElem = t.TypeVar("TElem")
T1 = t.TypeVar("T1")
T2 = t.TypeVar("T2")
T3 = t.TypeVar("T3")


@t.overload
def extract_types(
    elements: t.Iterable[TElem],
    __t1: type[T1],
) -> tuple[list[T1], list[TElem]]:
    ...


@t.overload
def extract_types(
    elements: t.Iterable[TElem],
    __t1: type[T1],
    __t2: type[T2],
) -> tuple[list[T1], list[T2], list[TElem]]:
    ...


@t.overload
def extract_types(
    elements: t.Iterable[TElem],
    __t1: type[T1],
    __t2: type[T2],
    __t3: type[T3],
) -> tuple[list[T1], list[T2], list[T3], list[TElem]]:
    ...


# add more overloads as needed
# /OVERLOADS


def extract_types(elements: t.Iterable[TElem], *types: type) -> tuple:
    """Extracts all elements of a certain type from an iterable.

    Unions work, but break the type hints because in mypy's eyes, ``int | float``
    is not an instance of ``type[int | float]``.

    If you want to get stricter typing of the `rest`, then either do a `cast` or use an
    additional type parameter and ``assert not rest`` to ensure that your assumption
    regarding the type bound is not violated.

    :param elements: The iterable to extract from
    :param type_: The type instance of which to extract to a separate list
    :return: A tuple ``(elements of specified type, other elements)``.

    >>> extract_types([1, 2, 3, "a", "b", "c"], int)
    ([1, 2, 3], ['a', 'b', 'c'])
    >>> extract_types([1, 2.0, 3, "a", "b", "c"], int, float)
    ([1, 3], [2.0], ['a', 'b', 'c'])
    >>> extract_types([1, 2.0, 3, "a", "b", "c"], int | float)
    ([1, 2.0, 3], ['a', 'b', 'c'])
    """
    by_type: tuple = ([],) * len(types)
    other = []
    for elem in elements:
        for i, type_ in enumerate(types):
            if isinstance(elem, type_):
                by_type[i].append(elem)
                break
        else:
            other.append(elem)
    return tuple((*by_type, other))


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
