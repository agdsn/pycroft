from abc import ABCMeta, abstractmethod

import ldap3

LDAP_OBJECTCLASSES = ['top', 'inetOrgPerson', 'posixAccount', 'shadowAccount']

class Action(object):
    __metaclass__ = ABCMeta

    def __init__(self, record):
        self.record = record

    @abstractmethod
    def execute(self, connection):
        pass


class AddAction(Action):
    def __init__(self, record):
        # We don't want to add e.g. an empty `mail` field
        record.remove_empty_attributes()
        super(AddAction, self).__init__(record)

    def execute(self, connection):
        connection.add(self.record.dn, LDAP_OBJECTCLASSES, self.record.attrs)


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
        connection.modify(dn=self.record.dn, changes={
            # attention: new_value might be list!
            attr: (ldap3.MODIFY_REPLACE, new_value)
            for attr, new_value in self.modifications.items()
        })


class DeleteAction(Action):
    def execute(self, connection):
        connection.delete(self.record.dn)


class IdleAction(Action):
    def execute(self, *a, **kw):
        pass
