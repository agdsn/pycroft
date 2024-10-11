import typing as t

from flask import url_for
from pydantic import BaseModel

from web.table.lazy_join import LazilyJoined
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
    DateColResponse,
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
    @t.override
    def toolbar(self) -> LazilyJoined:
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

    @t.override
    def __init__(self, *, room_id: int | None = None, **kw: t.Any) -> None:
        super().__init__(**kw)

        self.room_id = room_id

    @property
    @t.override
    def toolbar(self) -> LazilyJoined | None:
        if no_inf_change():
            return None
        href = url_for(".patch_port_create", switch_room_id=self.room_id)
        return button_toolbar("Patch-Port", href)


class PatchPortRow(BaseModel):
    name: str
    room: LinkColResponse
    switch_port: LinkColResponse | None = None
    edit_link: BtnColResponse
    delete_link: BtnColResponse


class RoomTenanciesTable(BootstrapTable):
    _render_toolbar = False

    inhabitant = BtnColumn("Bewohner")
    swdd_person_id = Column("Debitorennummer")
    begins_at = DateColumn("Von")
    ends_at = DateColumn("Bis")
    status = Column("Status")

    class Meta:
        table_args = {"data-sort-name": "begins_at"}


class RoomTenanciesRow(BaseModel):
    inhabitant: BtnColResponse | None = None
    swdd_person_id: int | None = None
    begins_at: DateColResponse
    ends_at: DateColResponse
    status: str
