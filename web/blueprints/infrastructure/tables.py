from flask import url_for
from flask_login import current_user
from wtforms.widgets import html_params

from web.blueprints.helpers.table import BootstrapTable, Column


class SubnetTable(BootstrapTable):
    def __init__(self, *a, **kw):
        super().__init__(*a, columns=[
            Column('#', 'id'),
            Column('Beschreibung', 'description'),
            Column('IP', 'address'),
            Column('Gateway', 'gateway'),
            Column('Reservierte Adressen', 'reserved',
                   formatter='table.listFormatter'),
            Column('Freie IPs', 'free_ips_formatted', col_args={
                'data-sort-name': 'free_ips',
            }),
        ], **kw)


class SwitchTable(BootstrapTable):
    def __init__(self, *a, **kw):
        super().__init__(*a, columns=[
            Column('#', 'id'),
            Column('Name', 'name', formatter='table.linkFormatter'),
            Column('Management IP', 'ip'),
            Column('Editieren', 'edit_link', formatter='table.btnFormatter', width=1),
            Column('Löschen', 'delete_link', formatter='table.btnFormatter', width=1)
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
            Column('#', 'id'),
            Column('Name', 'name'),
            Column('VID', 'vid'),
        ], **kw)


class PortTable(BootstrapTable):
    def __init__(self, *a, switch_id=None, **kw):
        super().__init__(*a, columns=[
            Column('Name', 'switchport_name', width=2),
            Column('→ Patchport', 'patchport_name', width=2),
            Column('→ Raum', 'room', formatter='table.linkFormatter', width=6),
            Column('Editieren', 'edit_link', formatter='table.btnFormatter'),
            Column('Löschen', 'delete_link', formatter='table.btnFormatter')
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
