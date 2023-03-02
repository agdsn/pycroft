# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
pycroft.helpers.i18n
~~~~~~~~~~~~~~~~~~~~
"""
from __future__ import annotations

from .deferred import (
    deferred_gettext,
    deferred_dgettext,
    deferred_ngettext,
    deferred_dngettext,
)
from .babel import (
    gettext,
    dgettext,
    ngettext,
    dngettext,
    get_locale,
    set_translation_lookup,
)
from .formatting import identity, format_param
from .message import Message, SimpleMessage, NumericalMessage
from .options import Options


def localized(json_string: str, options: Options | None = None) -> str:
    return Message.from_json(json_string).localize(options)


__all__ = (
    "get_locale",
    "set_translation_lookup",
    "Message",
    "localized",
    "gettext",
    "dngettext",
    "ngettext",
    "dgettext",
    "deferred_gettext",
    "deferred_dngettext",
    "deferred_ngettext",
    "deferred_dgettext",
)
