from flask import url_for
from flask_login import current_user

from web.blueprints.helpers.table import BootstrapTable, Column, LinkColumn, \
    button_toolbar, BtnColumn


class SiteTable(BootstrapTable):
    site = LinkColumn("Site")
    buildings = Column("Buildings", formatter='table.multiBtnFormatter')


class BuildingLevelRoomTable(BootstrapTable):
    class Meta:
        table_args = {
            'data-sort-name': 'room',
            'data-query-params': 'perhaps_all_users_query_params',
        }

    room = LinkColumn("Raum")
    inhabitants = Column('Bewohner', formatter='table.multiBtnFormatter')

    toolbar = button_toolbar("Display all users", href="#",
                             icon="glyphicon-user")


class RoomLogTable(BootstrapTable):
    created_at = Column("Erstellt um", formatter='table.dateFormatter')
    user = LinkColumn("Nutzer")
    message = Column("Nachricht")


class RoomOvercrowdedTable(BootstrapTable):
    room = LinkColumn("Raum")
    inhabitants = Column("Bewohner", formatter='table.multiBtnFormatter')

    class Meta:
        table_args = {'data-sort-name': 'room'}


class PatchPortTable(BootstrapTable):
    name = Column('Name', width=2)
    room = LinkColumn('→ Raum', width=5)
    switch_port = LinkColumn('→ Switch-Port', width=3)
    edit_link = BtnColumn('Editieren')
    delete_link = BtnColumn('Löschen')

    def __init__(self, *a, room_id=None, **kw):
        super().__init__(*a, **kw)

        self.room_id = room_id

    @property
    def toolbar(self):
        if not current_user.has_property('infrastructure_change'):
            return
        href = url_for(".patch_port_create", switch_room_id=self.room_id)
        return button_toolbar("Patch-Port", href)
