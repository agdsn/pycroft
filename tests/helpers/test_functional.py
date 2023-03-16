#  Copyright (c) 2023. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
import itertools

import pytest

from pycroft.helpers.functional import extract_types, flatten

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
