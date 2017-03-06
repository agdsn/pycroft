class Action(object):
    def __init__(self, record):
        self.record = record

    def execute(self, *a, **kw):
        raise NotImplementedError("Action subclass must implement `execute`.")


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
