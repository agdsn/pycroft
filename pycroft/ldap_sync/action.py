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
    def __init__(self, modifications, record):
        self.modifications = modifications
        super(ModifyAction, self).__init__(record)

    def execute(self, connection):
        raise NotImplementedError


class DeleteAction(Action):
    def execute(self, connection):
        connection.delete(self.record.dn)
