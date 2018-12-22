# -*- coding: utf-8; -*-
import logging
from abc import ABCMeta, abstractmethod

import ldap3


class Action(object, metaclass=ABCMeta):
    """An Action on an ldap record

    This represents an Action on a specific LDAP record, which may
    result in addition, deletion or modification.  In any way, a
    subclass must implement the :py:meth:`execute` method acting on an
    :py:obj:`ldap3.Connection`
    """

    def __init__(self, record, logger=None):
        self.record = record
        self.logger = (logger if logger is not None
                       else logging.getLogger('ldap_sync.action'))

    @abstractmethod
    def execute(self, connection):
        pass

    def debug_whether_success(self, connection):
        if connection.result['result']:
            self.logger.warning("Operation unsuccessful: %s", connection.result)
        else:
            self.logger.debug("Operation successful")

    def __repr__(self):
        return "<{} {}>".format(type(self).__name__, self.record.dn)

class AddAction(Action):
    def __init__(self, record):
        # We don't want to add e.g. an empty `mail` field
        record.remove_empty_attributes()
        super(AddAction, self).__init__(record)

    def execute(self, connection):
        self.logger.debug("Executing %s for %s", type(self).__name__, self.record.dn)
        self.logger.debug("Attributes used: %s", self.record.attrs)
        connection.add(self.record.dn, attributes=self.record.attrs)
        self.debug_whether_success(connection)

    def __repr__(self):
        return "<{} {}>".format(type(self).__name__, self.record.attrs['uid'][0])


class ModifyAction(Action):
    def __init__(self, record, modifications):
        """Initialize a new ModifyAction operating on `record` with
        `modifications`

        :param Record record:
        :param dict modifications: a dict with entries of the form
            ``'attribute_name': new_value``, where the value is a list
            if the corresponding attribute is not single-valued.
        """
        self.modifications = modifications
        super(ModifyAction, self).__init__(record)

    @classmethod
    def from_two_records(cls, current_record, desired_record):
        """Construct a ModifyAction from two records.

        This method doesn't check whether the dn is equal, it only
        acesses ``record.attrs``, respectively.

        This method also doesn't check whether both dicts have equal
        keys, meaning keys not given in :param:`desired_record.attrs`
        won't end up in the modification dict.  Removing attributes
        has to be done by explicitly setting them to an empty string.
        """
        current_attrs = current_record.attrs
        updated_attrs = desired_record.attrs
        for key, old_value in current_attrs.items():
            if key not in updated_attrs:
                continue
            if old_value == updated_attrs[key]:
                # we don't need to execute anupdate if the value doesn't change
                updated_attrs.pop(key)

        return cls(record=desired_record, modifications=updated_attrs)

    def execute(self, connection):
        self.logger.debug("Executing %s for %s (%s)", type(self).__name__, self.record.dn,
                          ', '.join(self.modifications))
        connection.modify(dn=self.record.dn, changes={
            # attention: new_value might be list!
            attr: (ldap3.MODIFY_REPLACE, new_value)
            for attr, new_value in self.modifications.items()
        })
        self.debug_whether_success(connection)

    def __repr__(self):
        attr_string = ', '.join(self.record.attrs.keys())
        return "<{} {} [{}]>".format(type(self).__name__, self.record.dn, attr_string)


class DeleteAction(Action):
    def execute(self, connection):
        self.logger.debug("Executing %s for %s", type(self).__name__, self.record.dn)
        connection.delete(self.record.dn)
        self.debug_whether_success(connection)


class IdleAction(Action):
    def execute(self, *a, **kw):
        # logging here would be useless noise, and would contradict the nature
        # of an “idle” action.
        pass
