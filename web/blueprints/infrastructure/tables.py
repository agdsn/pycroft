from flask import url_for
from flask_login import current_user

from web.blueprints.helpers.table import BootstrapTable, Column, LinkColumn, \
    BtnColumn, button_toolbar


def no_inf_change():
    return not current_user.has_property('infrastructure_change')


class SubnetTable(BootstrapTable):
    id = Column("#")
    description = Column("Beschreibung")
    address = Column("IP")
    gateway = Column("Gateway")
    reserved = Column("Reservierte Adressen", formatter='table.listFormatter',
                      sortable=False)
    free_ips_formatted = Column("Freie IPs", col_args={
        'data-sort-name': 'free_ips',
    })


class SwitchTable(BootstrapTable):
    id = Column("#")
    name = LinkColumn("Name")
    ip = Column("Management IP")
    edit_link = BtnColumn('Editieren', width=1, hide_if=no_inf_change)
    delete_link = BtnColumn('Löschen', width=1, hide_if=no_inf_change)

    @property
    def toolbar(self):
        if not current_user.has_property('infrastructure_change'):
            return

        return button_toolbar("Switch", url_for(".switch_create"))

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
    edit_link = BtnColumn('Editieren', hide_if=no_inf_change)
    delete_link = BtnColumn('Löschen', hide_if=no_inf_change)

    @property
    def toolbar(self):
        if no_inf_change():
            return
        href = url_for(".switch_port_create", switch_id=self.switch_id)
        return button_toolbar("Switch-Port", href)
