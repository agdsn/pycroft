#  Copyright (c) 2023. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
import itertools

import pytest

from pycroft.helpers.functional import (
    extract_types,
    flatten,
    with_catch,
    map_collecting_errors,
)

EXAMPLES = {
    int: [1, 2],
    str: ["a", "b"],
    float: [2.0, 3.0],
    type(None): [None, None],
}


TYPE_COMBINATIONS = list(
    flatten(itertools.combinations(EXAMPLES.keys(), n) for n in range(3))
)


@pytest.mark.parametrize(
    "args, expected, input",
    [
        (
            types,
            expected := (tuple(EXAMPLES[t] for t in types) + ([],)),
            list(flatten(expected)),
        )
        for types in TYPE_COMBINATIONS
    ],
)
def test_type_grouping_without_rest(input, args, expected):
    assert extract_types(input, *args) == expected


NONTRIVIAL_TYPE_COMBINATIONS = [c for c in TYPE_COMBINATIONS if c]


@pytest.mark.parametrize(
    "args, expected, input",
    [
        (
            types,
            expected := tuple(EXAMPLES[t] for t in types) + (EXAMPLES[other],),
            list(flatten(expected)),
        )
        for *types, other in NONTRIVIAL_TYPE_COMBINATIONS
    ],
)
def test_type_grouping_with_rest(input, args, expected):
    assert extract_types(input, *args) == expected


@pytest.mark.parametrize("input, expected", [("1", int), ("2", int), ("x", ValueError)])
def test_with_catch_int_conversion(input, expected):
    assert isinstance(with_catch(int, ValueError)(input), expected)


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
