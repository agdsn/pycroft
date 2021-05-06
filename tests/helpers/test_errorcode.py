# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import pytest

from pycroft.helpers.errorcode import digits, Type1Code, Type2Code, ErrorCode


@pytest.mark.parametrize('number, expected_list', [
    (0, [0]),
    (1234, [4, 3, 2, 1]),
    (-1234, [4, 3, 2, 1]),
])
def test_digits(number: int, expected_list: list[int]):
    assert list(digits(number)) == expected_list


VALID_RESULTS = [
    (Type1Code, 0, 0),
    (Type1Code, 1234, 0),
    (Type2Code, 0, 98),
    (Type2Code, 1234, 82),
]


@pytest.mark.parametrize('code, id, checksum', VALID_RESULTS)
def test_errorcode_calculation(code: ErrorCode, id: int, checksum: int):
    assert code.calculate(id) == checksum


@pytest.mark.parametrize('code, id, checksum', VALID_RESULTS)
def test_errorcode_validity(code: ErrorCode, id: int, checksum: int):
    assert code.is_valid(id, checksum)
