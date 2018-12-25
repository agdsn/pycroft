from flask import url_for
from flask_login import current_user
from wtforms.widgets import html_params

from web.blueprints.helpers.table import BootstrapTable, Column


class SiteTable(BootstrapTable):
    def __init__(self, *a, **kw):
        super().__init__(*a, columns=[
            Column('Site', 'site', formatter='table.linkFormatter'),
            Column('Buildings', 'buildings',
                   formatter='table.multiBtnFormatter'),
        ], **kw)


class BuildingLevelRoomTable(BootstrapTable):
    def __init__(self, *a, **kw):
        super().__init__(*a, columns=[
            Column('Raum', 'room', formatter='table.linkFormatter'),
            Column('Bewohner', 'inhabitants',
                   formatter='table.multiBtnFormatter'),
        ], table_args={
            'data-sort-name': 'room',
            'data-query-params': 'perhaps_all_users_query_params',
        }, **kw)

    def generate_toolbar(self):
        """Generate a toolbar with a "Display all users" button
        """
        yield '<a href="#" id="rooms-toggle-all-users" class="btn btn-default" role="button">'
        yield '<span class="glyphicon glyphicon-user"></span>'
        yield 'Display all users'
        yield '</a>'


class RoomLogTable(BootstrapTable):
    def __init__(self, *a, **kw):
        super().__init__(*a, columns=[
            Column('Erstellt um', 'created_at',
                   formatter='table.dateFormatter'),
            Column('Nutzer', 'user', formatter='table.linkFormatter'),
            Column('Nachricht', 'message'),
        ], **kw)


class RoomOvercrowdedTable(BootstrapTable):
    def __init__(self, *a, **kw):
        super().__init__(*a, columns=[
            Column('Raum', 'room', formatter='table.linkFormatter'),
            Column('Bewohner', 'inhabitants',
                   formatter='table.multiBtnFormatter'),
        ], table_args={
            'data-sort-name': 'room',
        }, **kw)


class PatchPortTable(BootstrapTable):
    def __init__(self, *a, room_id=None, **kw):
        super().__init__(*a, columns=[
            Column('name', 'Name', width=2),
            Column('room', '→ Raum', formatter='table.linkFormatter', width=5),
            Column('switch_port', '→ Switch-Port', formatter='table.linkFormatter', width=3),
            Column('edit_link', 'Editieren', formatter='table.btnFormatter'),
            Column('delete_link', 'Löschen', formatter='table.btnFormatter')
        ], **kw)

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

