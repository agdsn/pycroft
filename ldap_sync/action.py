#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
"""
ldap_sync.action
~~~~~~~~~~~~~~~~
Actions (Add/Delete/Modify/Nothing) and how to execute them.
"""
import dataclasses
import logging
import typing
from abc import ABC, abstractmethod

import ldap3

from . import types
from .record import Record  # shadowing…


def debug_whether_success(logger: logging.Logger, connection: ldap3.Connection) -> None:
    """Communicate whether the last operation on `connection` has been successful."""
    if connection.result['result']:
        logger.warning("Operation unsuccessful: %s", connection.result)
    else:
        logger.debug("Operation successful")


@dataclasses.dataclass  # type: ignore  # see https://github.com/python/mypy/issues/5374
class Action(ABC):
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

    @abstractmethod
    def execute(self, connection: ldap3.Connection) -> None:
        pass

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.record_dn}>"


class AddAction(Action):
    """Add an LDAP record"""
    nonempty_attrs: types.NormalizedAttributes

    def __init__(self, record: Record) -> None:
        # We don't want to add e.g. an empty `mail` field
        super().__init__(record_dn=record.dn)
        self.nonempty_attrs = {key: val for key, val in record.attrs.items() if val}

    def execute(self, connection: ldap3.Connection) -> None:
        self.logger.debug("Executing %s for %s", type(self).__name__, self.record_dn)
        self.logger.debug("Attributes used: %s", self.nonempty_attrs)
        connection.add(self.record_dn, attributes=self.nonempty_attrs)
        debug_whether_success(self.logger, connection)

# noinspection PyDataclass
@dataclasses.dataclass
class ModifyAction(Action):
    """Modify an LDAP record by changing its attributes."""

    #: a dict with entries of the form ``'attribute_name': new_value``,
    #: where the value is a list if the corresponding attribute is not single-valued.
    modifications: types.NormalizedAttributes

    def execute(self, connection: ldap3.Connection) -> None:
        self.logger.debug("Executing %s for %s (%s)", type(self).__name__, self.record_dn,
                          ', '.join(self.modifications))
        connection.modify(dn=self.record_dn, changes={
            # attention: new_value might be list!
            attr: (ldap3.MODIFY_REPLACE, new_value)
            for attr, new_value in self.modifications.items()
        })
        debug_whether_success(self.logger, connection)

    def __repr__(self) -> str:
        attr_string = ', '.join(self.modifications.keys())
        return f"<{type(self).__name__} {self.record_dn} [{attr_string}]>"


class DeleteAction(Action):
    """Delete an LDAP record."""

    def execute(self, connection: ldap3.Connection) -> None:
        self.logger.debug("Executing %s for %s", type(self).__name__, self.record_dn)
        connection.delete(self.record_dn)
        debug_whether_success(self.logger, connection)


class IdleAction(Action):
    """Do nothing."""

    def execute(self, *a: typing.Any, **kw: typing.Any) -> None:
        # logging here would be useless noise, and would contradict the nature
        # of an “idle” action.
        pass
