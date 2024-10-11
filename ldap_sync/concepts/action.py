#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
"""
ldap_sync.concepts.action
~~~~~~~~~~~~~~~~~~~~~~~~~
Actions (Add/Delete/Modify/Nothing)
"""
import dataclasses
import logging
import typing as t

from . import types
from .record import Record  # shadowing…


@dataclasses.dataclass
class Action:
    """Base class for the different actions the exporter can execute on an individual entity.

    An action in the sense of the LDAP export is something which

    * refers to a record (i.e. something with a DN)
    * can be executed (provided an LDAP connection).
    """

    record_dn: types.DN
    _: dataclasses.KW_ONLY  # pushes `logger=` back in generated `__init__`
    logger: logging.Logger = dataclasses.field(
        default_factory=lambda: logging.getLogger("ldap_sync.action")
    )

    @t.override
    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.record_dn}>"


class AddAction(Action):
    """Add an LDAP record"""

    nonempty_attrs: types.NormalizedAttributes

    @t.override
    def __init__(self, record: Record) -> None:
        # We don't want to add e.g. an empty `mail` field
        super().__init__(record_dn=record.dn)
        self.nonempty_attrs = {key: val for key, val in record.attrs.items() if val}


# noinspection PyDataclass
@dataclasses.dataclass
class ModifyAction(Action):
    """Modify an LDAP record by changing its attributes."""

    #: a dict with entries of the form ``'attribute_name': new_value``,
    #: where the value is a list if the corresponding attribute is not single-valued.
    modifications: types.NormalizedAttributes

    @t.override
    def __repr__(self) -> str:
        attr_string = ", ".join(self.modifications.keys())
        return f"<{type(self).__name__} {self.record_dn} [{attr_string}]>"


class DeleteAction(Action):
    """Delete an LDAP record."""


class IdleAction(Action):
    """Do nothing."""
