#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details

from __future__ import annotations

import typing

from babel import Locale
from babel.support import Translations

_unspecified_locale = Locale("en", "US")
_null_translations = Translations()
_locale_lookup: typing.Callable[[], Locale] = lambda: _unspecified_locale
_translations_lookup: typing.Callable[[], Translations] = lambda: _null_translations


def get_locale() -> Locale:
    return _locale_lookup()


def get_translations() -> Translations:
    return _translations_lookup()


def set_locale_lookup(lookup_func: typing.Callable[[], Locale]) -> None:
    global _locale_lookup
    _locale_lookup = lookup_func


def set_translation_lookup(lookup_func: typing.Callable[[], Translations]) -> None:
    global _translations_lookup
    _translations_lookup = lookup_func


def gettext(message: str) -> str:
    return typing.cast(str, get_translations().ugettext(message))


def dgettext(domain: str, message: str) -> str:
    return typing.cast(str, get_translations().udgettext(domain, message))


def ngettext(singular: str, plural: str, n: int) -> str:
    return typing.cast(str, get_translations().ungettext(singular, plural, n))


def dngettext(domain: str, singular: str, plural: str, n: int) -> str:
    return typing.cast(str, get_translations().udngettext(domain, singular, plural, n))
