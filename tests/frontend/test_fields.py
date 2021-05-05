# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import string

import pytest
from wtforms_widgets.fields.core import DateField

__author__ = 'shreyder'


def test_date_field_format_strings():
    for directive, replacement in DateField.supported_directives.items():
        assert DateField.convert_format_string("%" + directive) == replacement
        assert DateField.convert_format_string("%%" + directive) == "%" + directive

    for directive in DateField.unsupported_directives:
        with pytest.raises(ValueError):
            DateField.convert_format_string("%" + directive)
        assert DateField.convert_format_string("%%" + directive) == "%" + directive

    unknown_directives = set(string.ascii_letters).difference(
        set(DateField.supported_directives.keys()),
        set(DateField.unsupported_directives)
    )

    for directive in unknown_directives:
        with pytest.raises(ValueError):
            DateField.convert_format_string("%" + directive)

    assert DateField.convert_format_string("%%") == "%"
    assert DateField.convert_format_string("%%%%") == "%%"
