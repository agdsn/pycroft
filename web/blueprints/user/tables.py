from web.blueprints.helpers.table import BootstrapTable, Column


class LogTableExtended(BootstrapTable):
    def __init__(self, *a, **kw):
        super().__init__(*a, columns=[
            Column('created_at', 'Erstellt um', width=2),
            Column('type', 'Logtyp'),
            Column('user', 'Nutzer', formatter='userFormatter'),
            Column('message', 'Nachricht'),
        ], **kw)


class LogTableSpecific(BootstrapTable):
    def __init__(self, *a, **kw):
        super().__init__(*a, columns=[
            # specific tables don't need the `type`
            Column('created_at', 'Erstellt um', width=2),
            Column('user', 'Nutzer', formatter='userFormatter'),
            Column('message', 'Nachricht'),
        ], **kw)


class MembershipTable(BootstrapTable):
    def __init__(self, *a, **kw):
        super().__init__(*a, columns=[
            Column('group_name', 'Gruppe'),
            Column('begins_at', 'Beginn'),
            Column('ends_at', 'Ende'),
            Column('actions', 'Aktionen', formatter='multiBtnFormatter')
        ], **kw)


class HostTable(BootstrapTable):
    def __init__(self, *a, **kw):
        super().__init__(*a, columns=[
            Column('ip', 'IP-Adresse'),
            Column('mac', 'Mac-Adresse'),
            Column('switch', 'Switch'),
            Column('port', 'Switchport'),
            Column('action', 'MAC ändern', formatter='btnFormatter')
        ], **kw)


class FinanceTable(BootstrapTable):
    def __init__(self, *a, **kw):
        super().__init__(*a, columns=[
            Column('posted_at', 'Erstellt um'),
            Column('valid_on', 'Gültig am'),
            Column('description', 'Beschreibung', formatter='linkFormatter'),
            Column('amount', 'Wert'),
        ], **kw)
