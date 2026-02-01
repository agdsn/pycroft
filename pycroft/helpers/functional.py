#  Copyright (c) 2023. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
import typing as t


def map_collecting_errors[
    TIn, TOut, TErr: Exception
](
    func: t.Callable[[TIn], TOut],
    error_type: type[TErr],
    iterable: t.Iterable[TIn],
) -> tuple[list[TOut], list[TErr]]:
    results: list[TOut] = []
    errors: list[TErr] = []
    for x in iterable:
        try:
            results.append(func(x))
        except error_type as e:
            errors.append(e)
    return results, errors


def identity[T](x: T) -> T:
    return x
