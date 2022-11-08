#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
import contextlib
import typing as t


@contextlib.contextmanager
def assert_unchanged(
    *value_getter: t.Callable[[], t.Any],
    **named_value_getter: t.Callable[[], t.Any],
) -> t.Iterator[None]:
    old = [g() for g in value_getter]
    named_old = {k: g() for k, g in named_value_getter.items()}
    yield
    assert [g() for g in value_getter] == old
    assert {k: g() for k, g in named_value_getter.items()} == named_old
