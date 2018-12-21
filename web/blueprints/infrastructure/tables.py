from flask import url_for
from flask_login import current_user
from wtforms.widgets import html_params

from web.blueprints.helpers.table import BootstrapTable, Column


class SubnetTable(BootstrapTable):
    def __init__(self, *a, **kw):
        super().__init__(*a, columns=[
            Column('id', '#'),
            Column('description', 'Beschreibung'),
            Column('address', 'IP'),
            Column('gateway', 'Gateway'),
            Column('reserved', 'Reservierte Adressen',
                   formatter='table.listFormatter'),
            Column('free_ips_formatted', 'Freie IPs', col_args={
                'data-sort-name': 'free_ips',
            }),
        ], **kw)


class SwitchTable(BootstrapTable):
    def __init__(self, *a, **kw):
        super().__init__(*a, columns=[
            Column('id', '#'),
            Column('name', 'Name', formatter='table.linkFormatter'),
            Column('ip', 'Management IP'),
            Column('edit_link', 'Editieren', formatter='table.btnFormatter', width=1),
            Column('delete_link', 'Löschen', formatter='table.btnFormatter', width=1)
        ], **kw)

    def generate_toolbar(self):
        if not current_user.has_property('infrastructure_change'):
            return
        args = {
            'class': "btn btn-primary",
            'href': url_for(".switch_create"),
        }
        yield "<a {}>".format(html_params(**args))
        yield "<span class=\"glyphicon glyphicon-plus\"></span>"
        yield "Switch"
        yield "</a>"


class VlanTable(BootstrapTable):
    def __init__(self, *a, **kw):
        super().__init__(*a, columns=[
            Column('id', '#'),
            Column('name', 'Name'),
            Column('vid', 'VID'),
        ], **kw)


class PortTable(BootstrapTable):
    def __init__(self, *a, switch_id=None, **kw):
        super().__init__(*a, columns=[
            Column('switchport_name', 'Name', width=2),
            Column('patchport_name', '→ Patchport', width=2),
            Column('room', '→ Raum', formatter='table.linkFormatter', width=6),
            Column('edit_link', 'Editieren', formatter='table.btnFormatter'),
            Column('delete_link', 'Löschen', formatter='table.btnFormatter')
        ], **kw)

        self.switch_id = switch_id

    def generate_toolbar(self):
        if not current_user.has_property('infrastructure_change'):
            return
        args = {
            'class': "btn btn-primary",
            'href': url_for(".switch_port_create", switch_id=self.switch_id),
        }
        yield "<a {}>".format(html_params(**args))
        yield "<span class=\"glyphicon glyphicon-plus\"></span>"
        yield "Switch-Port"
        yield "</a>"
