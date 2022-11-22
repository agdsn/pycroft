#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
"""
pycroft.helpers.i18n.types
~~~~~~~~~~~~~~~~~~~~~~~~~~
"""
from __future__ import annotations

import collections

from ..interval import Interval, NegativeInfinity, PositiveInfinity, Bound

Money = collections.namedtuple("Money", ["value", "currency"])


__all__ = (
    "Money",
    "Interval",
    "NegativeInfinity",
    "PositiveInfinity",
    "Bound",
)
