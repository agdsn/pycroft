#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
"""
pycroft.helpers.i18n.deferred
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

from __future__ import annotations

from .message import SimpleMessage, NumericalMessage


def deferred_gettext(message) -> SimpleMessage:
    return SimpleMessage(message)


def deferred_dgettext(domain: str, message: str) -> SimpleMessage:
    return SimpleMessage(message, domain)


def deferred_ngettext(singular, plural, n) -> NumericalMessage:
    return NumericalMessage(singular, plural, n)


def deferred_dngettext(domain, singular, plural, n) -> NumericalMessage:
    return NumericalMessage(singular, plural, n, domain)
