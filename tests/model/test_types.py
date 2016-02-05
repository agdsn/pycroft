# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from unittest import TestCase

from decimal import Decimal
from pycroft.model.types import Money


class MoneyTypeDecorator(TestCase):
    correct_pairs = {1234: [Decimal('12.34')],
                      550: [5.5, Decimal('5.50')],
                     1000: [10, 10., Decimal('10')],
                        1: [Decimal('0.01')],
                        0: [0, 0., Decimal('-0'), Decimal('0')],
                      -10: [Decimal('-0.1')],
                      -50: [-0.5, Decimal('-0.5')],
                     }

    def test_0010_process_bind_param(self):
        errors = ["not a number",
                  "235",
                  0.1,  # (not an exact representation)
                  -0.7,
                  Decimal('-2.003'),
                  Decimal('0.005')]

        for rv, bps in self.correct_pairs.items():
            for bp in bps:
                self.assertEqual(Money.process_bind_param(bp, None), rv)

        for bp in errors:
            with self.assertRaises(ValueError):
                Money.process_bind_param(bp, None)

    def test_0020_invertedness(self):
        for rv in self.correct_pairs.keys():
            self.assertEqual(rv,
                             Money.process_bind_param(
                                 Money.process_result_value(rv, None), None))
