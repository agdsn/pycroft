from flask import url_for
from flask_login import current_user
from wtforms.widgets import html_params

from web.blueprints.helpers.table import BootstrapTable, Column


class SiteTable(BootstrapTable):
    site = Column("Site", formatter='table.linkFormatter')
    buildings = Column("Buildings", formatter='table.multiBtnFormatter')


class BuildingLevelRoomTable(BootstrapTable):
    def __init__(self, *a, **kw):
        super().__init__(*a, table_args={
            'data-sort-name': 'room',
            'data-query-params': 'perhaps_all_users_query_params',
        }, **kw)

    room = Column("Raum", formatter='table.linkFormatter')
    inhabitants = Column('Bewohner', formatter='table.multiBtnFormatter')

    def generate_toolbar(self):
        """Generate a toolbar with a "Display all users" button
        """
        yield '<a href="#" id="rooms-toggle-all-users" class="btn btn-default" role="button">'
        yield '<span class="glyphicon glyphicon-user"></span>'
        yield 'Display all users'
        yield '</a>'


class RoomLogTable(BootstrapTable):
    created_at = Column("Erstellt um", formatter='table.dateFormatter')
    user = Column("Nutzer", formatter='table.linkFormatter')
    message = Column("Nachricht")


class RoomOvercrowdedTable(BootstrapTable):
    room = Column("Raum", formatter='table.linkFormatter')
    inhabitants = Column("Bewohner", formatter='table.multiBtnFormatter')

    def __init__(self, *a, **kw):
        super().__init__(*a, table_args={'data-sort-name': 'room'}, **kw)


class PatchPortTable(BootstrapTable):
    name = Column('Name', width=2)
    room = Column('→ Raum', formatter='table.linkFormatter', width=5)
    switch_port = Column('→ Switch-Port', formatter='table.linkFormatter', width=3)
    edit_link = Column('Editieren', formatter='table.btnFormatter')
    delete_link = Column('Löschen', formatter='table.btnFormatter')

    def __init__(self, *a, room_id=None, **kw):
        super().__init__(*a, **kw)

        self.room_id = room_id

    def generate_toolbar(self):
        if not current_user.has_property('infrastructure_change'):
            return
        args = {
            'class': "btn btn-primary",
            'href': url_for(".patch_port_create", switch_room_id=self.room_id),
        }
        yield "<a {}>".format(html_params(**args))
        yield "<span class=\"glyphicon glyphicon-plus\"></span>"
        yield "Patch-Port"
        yield "</a>"
