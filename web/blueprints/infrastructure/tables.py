from web.blueprints.helpers.table import BootstrapTable, Column


class SubnetTable(BootstrapTable):
    def __init__(self, *a, **kw):
        super().__init__(*a, columns=[
            Column('id', '#'),
            Column('description', 'Beschreibung'),
            Column('address', 'IP'),
            Column('gateway', 'Gateway'),
        ], **kw)


class SwitchTable(BootstrapTable):
    def __init__(self, *a, **kw):
        super().__init__(*a, columns=[
            Column('id', '#'),
            Column('name', 'Name', formatter='table.linkFormatter'),
            Column('ip', 'Management IP'),
        ], **kw)


class VlanTable(BootstrapTable):
    def __init__(self, *a, **kw):
        super().__init__(*a, columns=[
            Column('id', '#'),
            Column('name', 'Name'),
            Column('vid', 'VID'),
        ], **kw)


class PortTable(BootstrapTable):
    def __init__(self, *a, **kw):
        super().__init__(*a, columns=[
            Column('portname', 'Name', width=2),
            Column('room', 'Raum', formatter='table.linkFormatter', width=10),
        ], **kw)
