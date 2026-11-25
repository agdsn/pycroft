"""
pycroft.helpers.i18n.options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

from __future__ import annotations

import typing

type TypeSpecificOptions = dict[str, typing.Any]
OptionPolicy = typing.Literal["type-specific", "ignore"]
type Options = dict[type, TypeSpecificOptions]
