#  Copyright (c) 2023. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
import pytest

from pycroft.helpers.functional import map_collecting_errors


@pytest.mark.parametrize(
    "input",
    [
        [1, 2, 3],
        [object(), 0, 7, "foo", None],
        list(reversed([object(), 0, 7, "foo", None])),
        [],
        [None],
        [float("NaN")],
    ],
)
@pytest.mark.parametrize("error_type", [Exception, ZeroDivisionError, ValueError])
def test_identity_no_error_collection(input, error_type):
    assert map_collecting_errors(lambda x: x, error_type, input) == (list(input), [])


@pytest.mark.parametrize(
    "input, expected_result",
    [
        ([1, 0, 2, 0, 3], [1, 2, 3]),
        ([1, 0, 2, 0, 3, 0], [1, 2, 3]),
        ([0, 1, 0, 2, 0, 3], [1, 2, 3]),
        ([0, 1, 0, 2, 0, 3, 0], [1, 2, 3]),
    ],
)
def test_error_collection_inversion(input, expected_result):
    result, errors = map_collecting_errors(
        lambda x: 1 / (1 / x), ZeroDivisionError, input
    )
    assert result == expected_result
    assert len(errors) == len(input) - len(expected_result)
    assert all(isinstance(err, ZeroDivisionError) for err in errors)
