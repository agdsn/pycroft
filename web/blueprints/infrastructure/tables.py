from flask import url_for
from flask_login import current_user
from wtforms.widgets import html_params

from web.blueprints.helpers.table import BootstrapTable, Column, LinkColumn, \
    BtnColumn


class SubnetTable(BootstrapTable):
    id = Column("#")
    description = Column("Beschreibung")
    address = Column("IP")
    gateway = Column("Gateway")
    reserved = Column("Reservierte Adressen", formatter='table.listFormatter')
    free_ips_formatted = Column("Freie IPs", col_args={
        'data-sort-name': 'free_ips',
    })


class SwitchTable(BootstrapTable):
    id = Column("#")
    name = LinkColumn("Name")
    ip = Column("Management IP")
    edit_link = Column('Editieren', formatter='table.btnFormatter', width=1)
    delete_link = Column('Löschen', formatter='table.btnFormatter', width=1)

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
    id = Column("#")
    name = Column("Name")
    vid = Column("VID")


class PortTable(BootstrapTable):
    def __init__(self, *a, switch_id=None, **kw):
        super().__init__(*a, **kw)
        self.switch_id = switch_id

    switchport_name = Column("Name", width=2)
    patchport_name = Column("→ Patchport", width=2)
    room = LinkColumn("→ Raum", width=10)
    edit_link = BtnColumn('Editieren')
    delete_link = BtnColumn('Löschen')

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
