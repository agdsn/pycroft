from flask import url_for
from pydantic import BaseModel

from web.table.table import (
    BootstrapTable,
    Column,
    LinkColumn,
    button_toolbar,
    toggle_button_toolbar,
    BtnColumn,
    MultiBtnColumn,
    DateColumn,
    LinkColResponse,
    BtnColResponse,
)
from web.blueprints.infrastructure.tables import no_inf_change


class SiteTable(BootstrapTable):
    site = LinkColumn("Site")
    buildings = MultiBtnColumn("Buildings")


class SiteRow(BaseModel):
    site: LinkColResponse
    buildings: list[BtnColResponse]


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
        return toggle_button_toolbar(
            "Display all users",
            id="rooms-toggle-all-users",
            icon="fa-user"
        )


class BuildingLevelRoomRow(BaseModel):
    room: LinkColResponse
    inhabitants: list[BtnColResponse]


class RoomLogTable(BootstrapTable):
    """Like a log table, just with absolute date column"""
    created_at = DateColumn("Erstellt um")
    user = LinkColumn("Nutzer")
    message = Column("Nachricht")


class RoomOvercrowdedTable(BootstrapTable):
    room = LinkColumn("Raum")
    inhabitants = MultiBtnColumn("Bewohner")

    class Meta:
        table_args = {'data-sort-name': 'room'}


class RoomOvercrowdedRow(BaseModel):
    room: LinkColResponse
    inhabitants: list[BtnColResponse]


class PatchPortTable(BootstrapTable):
    class Meta:
        table_args = {
            'data-sort-name': 'name',
        }

    name = Column('Name', width=2, col_args={'data-sorter': 'table.sortPatchPort'})
    room = LinkColumn('→ Raum', width=5)
    switch_port = LinkColumn('→ Switch-Port', width=3, col_args={'data-sorter': 'table.sortPort'})
    edit_link = BtnColumn('Editieren', hide_if=no_inf_change)
    delete_link = BtnColumn('Löschen', hide_if=no_inf_change)

    def __init__(self, *a, room_id=None, **kw) -> None:
        super().__init__(*a, **kw)

        self.room_id = room_id

    @property
    def toolbar(self):
        if no_inf_change():
            return
        href = url_for(".patch_port_create", switch_room_id=self.room_id)
        return button_toolbar("Patch-Port", href)


class PatchPortRow(BaseModel):
    name: str
    room: LinkColResponse
    switch_port: LinkColResponse
    edit_link: BtnColResponse
    delete_link: BtnColResponse
