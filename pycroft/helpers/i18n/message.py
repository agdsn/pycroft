#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
from __future__ import annotations

import abc
import json
import traceback
import typing
from functools import partial

import jsonschema

from .babel import gettext, dgettext, dngettext, ngettext
from .formatting import format_param
from .options import Options
from .serde import Serializable, serialize_param, deserialize_param


# TODO remove in py3.11 (replace `TSelf` by `Self`)
TMessage = typing.TypeVar("TMessage", bound="Message")


class Message(abc.ABC):
    __slots__ = ("domain", "args", "kwargs")

    @classmethod
    def from_json(cls, json_string: str) -> Message:
        try:
            obj = json.loads(json_string)
        except ValueError:
            return ErroneousMessage(json_string)
        try:
            jsonschema.validate(obj, schema)
        except jsonschema.ValidationError as e:
            return ErroneousMessage(
                "Message validation failed: {} for " "message {}".format(e, json_string)
            )
        args = obj.get("args", ())
        kwargs = obj.get("kwargs", {})
        try:
            args = tuple(deserialize_param(a) for a in args)
            kwargs = {k: deserialize_param(v) for k, v in kwargs.items()}
        except (TypeError, ValueError) as e:
            error = "".join(traceback.format_exception_only(type(e), e))
            return ErroneousMessage(
                "Parameter deserialization error: {} in "
                "message: {}".format(error, json_string)
            )
        m: Message
        if "plural" in obj:
            m = NumericalMessage(
                obj["singular"], obj["plural"], obj["n"], obj.get("domain")
            )
        else:
            m = SimpleMessage(obj["message"], obj.get("domain"))
        m.args = args
        m.kwargs = kwargs
        return m

    def __init__(self, domain: str | None = None):
        self.domain = domain
        self.args: typing.Iterable[Serializable] = ()
        self.kwargs: dict[str, Serializable] = {}

    @abc.abstractmethod
    def _base_dict(self) -> dict[str, typing.Any]:
        ...

    @abc.abstractmethod
    def _gettext(self) -> str:
        ...

    def to_json(self) -> str:
        obj = self._base_dict()
        if self.domain is not None:
            obj["domain"] = self.domain
        if self.args:
            obj["args"] = tuple(serialize_param(a) for a in self.args)
        if self.kwargs:
            obj["kwargs"] = {k: serialize_param(v) for k, v in self.kwargs.items()}
        return json.dumps(obj, ensure_ascii=False)

    def format(self: TMessage, *args: Serializable, **kwargs: Serializable) -> TMessage:
        self.args = args
        self.kwargs = kwargs
        return self

    def localize(self, options: Options = None) -> str:
        if options is None:
            options = dict()

        msg = self._gettext()
        if not self.args and not self.kwargs:
            return msg
        f = partial(format_param, options=options)
        try:
            args = tuple(f(a) for a in self.args)
            kwargs = {k: f(v) for k, v in self.kwargs.items()}
            return msg.format(*args, **kwargs)
        except (TypeError, ValueError, IndexError, KeyError) as e:
            error = "".join(traceback.format_exception_only(type(e), e))
            return gettext(
                'Could not format message "{message}" '
                "(args={args}, kwargs={kwargs}): {error}"
            ).format(message=msg, args=self.args, kwargs=self.kwargs, error=error)


class ErroneousMessage(Message):
    def __init__(self, text):
        super().__init__(None)
        self.text = text

    def _base_dict(self):
        raise AssertionError("ErroneousMessage should never be serialized")

    def _gettext(self):
        return self.text


class SimpleMessage(Message):
    __slots__ = ("message",)

    def __init__(self, message, domain=None):
        super().__init__(domain)
        self.message = message

    def _base_dict(self):
        return {"message": self.message}

    def _gettext(self):
        if self.domain:
            return dgettext(self.domain, self.message)
        else:
            return gettext(self.message)


class NumericalMessage(Message):
    __slots__ = ("singular", "plural", "n")

    def __init__(self, singular, plural, n, domain=None):
        super().__init__(domain)
        self.singular = singular
        self.plural = plural
        self.n = n

    def _base_dict(self):
        return {"singular": self.singular, "plural": self.plural, "n": self.n}

    def _gettext(self):
        if self.domain:
            return dngettext(self.domain, self.singular, self.plural, self.n)
        else:
            return ngettext(self.singular, self.plural, self.n)


schema = {
    "id": "http://agdsn.de/localized-schema#",
    "$schema": "http://json-schema.org/draft-04/schema#",
    "description": "Message format for deferred localization.",
    "oneOf": [
        {"$ref": "#/definitions/simple"},
        {"$ref": "#/definitions/numerical"},
    ],
    "definitions": {
        "simple": {
            "type": "object",
            "properties": {
                "domain": {"type": "string"},
                "message": {"type": "string"},
                "args": {"$ref": "#/definitions/args"},
                "kwargs": {"$ref": "#/definitions/kwargs"},
            },
            "required": ["message"],
            "additionalProperties": False,
        },
        "numerical": {
            "type": "object",
            "properties": {
                "domain": {"type": "string"},
                "singular": {"type": "string"},
                "n": {"type": "integer"},
                "plural": {"type": "string"},
                "args": {"$ref": "#/definitions/args"},
                "kwargs": {"$ref": "#/definitions/kwargs"},
            },
            "required": ["singular", "plural", "n"],
            "additionalProperties": False,
        },
        "args": {"type": "array", "items": {"$ref": "#/definitions/param"}},
        "kwargs": {
            "type": "object",
            "patternProperties": {
                "^[a-zA-Z_][a-zA-Z0-9_]+": {"$ref": "#/definitions/param"}
            },
            "additionalProperties": False,
        },
        "param": {
            "type": "object",
            "properties": {
                "type": {"type": "string"},
                "value": {},
            },
            "required": ["type", "value"],
            "additionalProperties": False,
        },
    },
}
