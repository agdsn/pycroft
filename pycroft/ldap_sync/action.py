from abc import ABCMeta, abstractmethod

class Action(object):
    __metaclass__ = ABCMeta

    def __init__(self, record):
        self.record = record

    @abstractmethod
    def execute(self, *a, **kw):
        pass


class AddAction(Action):
    def execute(self, connection):
        #TODO: Correct ldap objectclasses?
        connection.add(self.record.dn, ['inetOrgPerson'], self.record.attrs)


class ModifyAction(Action):
    def __init__(self, record, modifications):
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
        raise NotImplementedError


class DeleteAction(Action):
    def execute(self, connection):
        connection.delete(self.record.dn)


class IdleAction(Action):
    def execute(self, *a, **kw):
        pass
