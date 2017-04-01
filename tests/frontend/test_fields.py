# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import string
from unittest import TestCase
from web.form.fields.core import DateField

__author__ = 'shreyder'


class Test_010_BootstrapDatepicker(TestCase):
    def test_0010_convert_format_string(self):
        for directive, replacement in DateField.supported_directives.items():
            self.assertEqual(
                DateField.convert_format_string("%" + directive),
                replacement
            )
            self.assertEqual(
                DateField.convert_format_string("%%" + directive),
                "%" + directive
            )
        for directive in DateField.unsupported_directives:
            self.assertRaises(
                ValueError,
                DateField.convert_format_string, "%" + directive
            )
            self.assertEqual(
                DateField.convert_format_string("%%" + directive),
                "%" + directive
            )
        unknown_directives = set(string.ascii_letters).difference(
            set(DateField.supported_directives.keys()),
            set(DateField.unsupported_directives)
        )
        for directive in unknown_directives:
            self.assertRaises(
                ValueError,
                DateField.convert_format_string, "%" + directive
            )

        self.assertEqual("", "")
        self.assertEqual(DateField.convert_format_string("%%"), "%")
        self.assertEqual(DateField.convert_format_string("%%%%"), "%%")
