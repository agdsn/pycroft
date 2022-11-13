from __future__ import annotations

import typing

TypeSpecificOptions: typing.TypeAlias = dict[str, typing.Any]
OptionPolicy = typing.Literal["type-specific", "ignore"]
Options: typing.TypeAlias = dict[type, TypeSpecificOptions]
