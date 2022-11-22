#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
"""
pycroft.helpers.i18n.utils
~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

from __future__ import annotations


def qualified_typename(type_: type) -> str:
    return type_.__module__ + "." + type_.__name__
