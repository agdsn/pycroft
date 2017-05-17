from web.blueprints.helpers.table import BootstrapTable, Column, SplittedTable


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
        table_args = {
            'data-row-style': 'financeRowFormatter',
            'data-side-pagination': 'server',
            # 'data-search': 'true',
            'data-sort-order': 'desc',
            'data-sort-name': 'valid_on',
        }
        original_table_args = kw.pop('table_args', {})
        table_args.update(original_table_args)
        super().__init__(*a, columns=[
            Column(name='posted_at', title='Erstellt um'),
            Column(name='valid_on', title='Gültig am'),
            Column(name='description', title='Beschreibung', formatter='linkFormatter'),
            Column(name='amount', title='Wert'),
        ], table_args=table_args, **kw)


class FinanceTableSplitted(FinanceTable, SplittedTable):
    def __init__(self, *a, **kw):
        splits = (('soll', "Soll"), ('haben', "Haben"))
        table_args = {
            'data-row-style': False,
            'data-sort-name': False,  # the "valid_on" col doesn't exist here
        }
        table_args.update(kw.pop('table_args', {}))
        super().__init__(*a, splits=splits, table_args=table_args, **kw)
