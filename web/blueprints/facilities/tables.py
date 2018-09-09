from web.blueprints.helpers.table import BootstrapTable, Column


class SiteTable(BootstrapTable):
    def __init__(self, *a, **kw):
        super().__init__(*a, columns=[
            Column('site', 'Site', formatter='table.linkFormatter'),
            Column('buildings', 'Buildings', formatter='table.multiBtnFormatter'),
        ], **kw)


class BuildingLevelRoomTable(BootstrapTable):
    def __init__(self, *a, **kw):
        super().__init__(*a, columns=[
            Column('room', 'Raum', formatter='table.linkFormatter'),
            Column('inhabitants', 'Bewohner', formatter='table.multiBtnFormatter'),
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
            Column('created_at', 'Erstellt um', formatter='table.dateFormatter'),
            Column('user', 'Nutzer', formatter='table.linkFormatter'),
            Column('message', 'Nachricht'),
        ], **kw)
