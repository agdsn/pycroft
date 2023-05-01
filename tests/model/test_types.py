# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from decimal import Decimal

import pytest

from pycroft.model.types import Money, MACAddress


class TestMoneyType:
    CORRECT_PAIRS = {
        1234: [Decimal('12.34')],
        550: [5.5, Decimal('5.50')],
        1000: [10, 10., Decimal('10')],
        1: [Decimal('0.01')],
        0: [0, 0., Decimal('-0'), Decimal('0')],
        -10: [Decimal('-0.1')],
        -50: [-0.5, Decimal('-0.5')],
    }

    @pytest.mark.parametrize('rv, bp', [
        (key, valid_input)
        for key, valid_inputs in CORRECT_PAIRS.items()
        for valid_input in valid_inputs
    ])
    def test_bind_param(self, rv, bp):
        assert Money.process_bind_param(bp, None) == rv

    @pytest.mark.parametrize('erroneous_bind', [
        "not a number",
        "235",
        0.1,  # (not an exact representation)
        -0.7,
        Decimal('-2.003'),
        Decimal('0.005')
    ])
    def test_bind_param_errors(self, erroneous_bind):
        with pytest.raises(ValueError):
            Money.process_bind_param(erroneous_bind, None)

    @pytest.mark.parametrize('rv', list(CORRECT_PAIRS.keys()))
    def test_inversion(self, rv):
        assert rv == Money.process_bind_param(Money.process_result_value(rv, None), None)

class TestMACType:
    CORRECT_VALUES = {
        "value": ["12:12:12:12:12:12", "FF:FF:FF:FF:FF:FF", "12:da:Ac:12:22:22"],
        "postgres": [
            "{12}:{12}:{12}:{12}:{12}:{12}",
            "{FF}:{FF}:{FF}:{FF}:{FF}:{FF}",
            "{12}:{da}:{Ac}:{12}:{22}:{22}",
        ],
    }
    mac = MACAddress

    @pytest.mark.parametrize("rv", CORRECT_VALUES)
    def test_bind_param(self, rv):
        assert self.mac.process_bind_param(None, rv["value"], None) == rv.replace(
            ":", ""
        )

    @pytest.mark.parametrize("rv", [None, ""])
    def test_bind_param_empty_str(self, rv):
        assert self.mac.process_bind_param(None, rv, None) is None

    @pytest.mark.parametrize(
        "rv", ["12:12:12:12", "FF:FF:FF:FF:FF", "asfdawd", "FF:FF:FF:FF:FF:wF"]
    )
    def test_bind_param_error(self, rv):
        with pytest.raises(ValueError):
            self.mac.process_bind_param(None, rv, None)
