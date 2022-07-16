#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
"""
Actions (Add/Delete/Modify/Nothing) and how to execute them.
"""
import logging
from abc import ABCMeta, abstractmethod

import ldap3

from . import record, types


def debug_whether_success(logger: logging.Logger, connection: ldap3.Connection) -> None:
    """Communicate whether the last operation on `connection` has been successful."""
    if connection.result['result']:
        logger.warning("Operation unsuccessful: %s", connection.result)
    else:
        logger.debug("Operation successful")


class Action(metaclass=ABCMeta):
    """An Action on an ldap record

    This represents an Action on a specific LDAP record, which may
    result in addition, deletion or modification.  In any way, a
    subclass must implement the :py:meth:`execute` method acting on an
    :py:obj:`ldap3.Connection`
    """

    def __init__(self, record_dn: str, logger: logging.Logger | None = None) -> None:
        self.record_dn = record_dn
        self.logger = (logger if logger is not None
                       else logging.getLogger('ldap_sync.action'))

    @abstractmethod
    def execute(self, connection):
        pass

    def __repr__(self):
        return f"<{type(self).__name__} {self.record_dn}>"

class AddAction(Action):
    def __init__(self, record: record.Record) -> None:
        # We don't want to add e.g. an empty `mail` field
        super().__init__(record_dn=record.dn)
        self.record = record
        record.remove_empty_attributes()

    def execute(self, connection):
        self.logger.debug("Executing %s for %s", type(self).__name__, self.record.dn)
        self.logger.debug("Attributes used: %s", self.record.attrs)
        connection.add(self.record.dn, attributes=self.record.attrs)
        debug_whether_success(self.logger, connection)

    def __repr__(self):
        return f"<{type(self).__name__} {self.record.dn}>"


class ModifyAction(Action):
    def __init__(self, record_dn, modifications: types.NormalizedAttributes) -> None:
        """Initialize a new ModifyAction operating on `record` with
        `modifications`

        :param record_dn:
        :param dict modifications: a dict with entries of the form
            ``'attribute_name': new_value``, where the value is a list
            if the corresponding attribute is not single-valued.
            :param record_dn:
        """
        super().__init__(record_dn=record_dn)
        self.modifications = modifications

    def execute(self, connection):
        self.logger.debug("Executing %s for %s (%s)", type(self).__name__, self.record_dn,
                          ', '.join(self.modifications))
        connection.modify(dn=self.record_dn, changes={
            # attention: new_value might be list!
            attr: (ldap3.MODIFY_REPLACE, new_value)
            for attr, new_value in self.modifications.items()
        })
        debug_whether_success(self.logger, connection)

    def __repr__(self):
        attr_string = ', '.join(self.modifications.keys())
        return f"<{type(self).__name__} {self.record_dn} [{attr_string}]>"


class DeleteAction(Action):
    def execute(self, connection):
        self.logger.debug("Executing %s for %s", type(self).__name__, self.record_dn)
        connection.delete(self.record_dn)
        debug_whether_success(self.logger, connection)


class IdleAction(Action):
    def execute(self, *a, **kw):
        # logging here would be useless noise, and would contradict the nature
        # of an “idle” action.
        pass
