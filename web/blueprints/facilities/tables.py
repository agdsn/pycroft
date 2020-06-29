from flask import url_for

from bs_table_py.table import BootstrapTable, Column, LinkColumn, \
    button_toolbar, BtnColumn, MultiBtnColumn, DateColumn
from web.blueprints.infrastructure.tables import no_inf_change


class SiteTable(BootstrapTable):
    site = LinkColumn("Site")
    buildings = MultiBtnColumn("Buildings")


class BuildingLevelRoomTable(BootstrapTable):
    class Meta:
        table_args = {
            'data-sort-name': 'room',
            'data-query-params': 'perhaps_all_users_query_params',
        }

    room = LinkColumn("Raum")
    inhabitants = MultiBtnColumn('Bewohner')

    @property
    def toolbar(self):
        return button_toolbar(
            "Display all users", href="#", id="rooms-toggle-all-users",
            icon="fa-user")


class RoomLogTable(BootstrapTable):
    created_at = DateColumn("Erstellt um")
    user = LinkColumn("Nutzer")
    message = Column("Nachricht")


class RoomOvercrowdedTable(BootstrapTable):
    room = LinkColumn("Raum")
    inhabitants = MultiBtnColumn("Bewohner")

    class Meta:
        table_args = {'data-sort-name': 'room'}


class PatchPortTable(BootstrapTable):
    name = Column('Name', width=2)
    room = LinkColumn('→ Raum', width=5)
    switch_port = LinkColumn('→ Switch-Port', width=3)
    edit_link = BtnColumn('Editieren', hide_if=no_inf_change)
    delete_link = BtnColumn('Löschen', hide_if=no_inf_change)

    def __init__(self, *a, room_id=None, **kw):
        super().__init__(*a, **kw)

        self.room_id = room_id

    @property
    def toolbar(self):
        if no_inf_change():
            return
        href = url_for(".patch_port_create", switch_room_id=self.room_id)
        return button_toolbar("Patch-Port", href)
