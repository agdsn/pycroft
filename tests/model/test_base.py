# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import pytest

from pycroft.model.base import ModelBase


@pytest.mark.parametrize('value, expected', [
    ("Noun", "noun"),
    ("HTML", "html"),
    ("HTML40", "html40"),
    ("HTMLParser", "html_parser"),
    ("HTML40Parser", "html40_parser"),
    ("SafeHTML", "safe_html"),
    ("Version2CSV", "version2_csv"),
])
def test_snake_case_conversion(value, expected):
    assert ModelBase._to_snake_case(value) == expected
