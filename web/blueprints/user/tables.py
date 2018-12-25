from flask import url_for
from flask_login import current_user
from wtforms.widgets.core import html_params

from web.blueprints.helpers.table import BootstrapTable, Column


class RefreshableTableMixin:
    """A mixin class showing the refresh button by default.

    In :py:meth:`__init__`s ``table_args`` argument, a default of
    ``{'data-show-refresh': "true"}`` is established.
    """
    def __init__(self, *a, **kw):
        table_args = kw.pop('table_args', {})
        table_args.setdefault('data-show-refresh', "true")
        kw['table_args'] = table_args
        super().__init__(*a, **kw)


class LogTableExtended(RefreshableTableMixin, BootstrapTable):
    """A table for displaying logs, with a ``type`` column"""
    def __init__(self, *a, **kw):
        super().__init__(*a, columns=[
            Column('Erstellt um', 'created_at', formatter='table.dateFormatter',
                   width=2),
            Column('Logtyp', 'type'),
            Column('Nutzer', 'user', formatter='table.userFormatter'),
            Column('Nachricht', 'message'),
        ], **kw)


class LogTableSpecific(RefreshableTableMixin, BootstrapTable):
    """A table for displaying logs"""
    def __init__(self, *a, **kw):
        super().__init__(*a, columns=[
            # specific tables don't need the `type`
            Column('Erstellt um', 'created_at', formatter='table.dateFormatter',
                   width=2),
            Column('Nutzer', 'user', formatter='table.userFormatter'),
            Column('Nachricht', 'message'),
        ], **kw)


class MembershipTable(BootstrapTable):
    """A table for displaying memberships

    In the toolbar, a “new membership” button is inserted if the
    :py:obj:`current_user` has the ``add_membership`` property.
    """
    def __init__(self, *a, user_id=None, **kw):
        super().__init__(*a, columns=[
            Column('Gruppe', 'group_name'),
            Column('Beginn', 'begins_at', formatter='table.dateFormatter'),
            Column('Ende', 'ends_at', formatter='table.dateFormatter'),
            Column('Aktionen', 'actions', formatter='table.multiBtnFormatter')
        ], **kw)
        self.user_id = user_id

    def generate_toolbar(self):
        if self.user_id is None:
            return
        if not current_user.has_property('groups_change_membership'):
            return
        args = {
            'class': "btn btn-primary",
            'href': url_for(".add_membership", user_id=self.user_id),
        }
        yield "<a {}>".format(html_params(**args))
        yield "<span class=\"glyphicon glyphicon-plus\"></span>"
        yield "Mitgliedschaft"
        yield "</a>"


class HostTable(BootstrapTable):
    """A table for displaying hosts
    """
    def __init__(self, *a, user_id=None, **kw):
        super().__init__(*a, columns=[
            Column('Name', 'name'),
            Column('Switch', 'switch'),
            Column('Switchport', 'port'),
            Column('Editieren', 'edit_link', formatter='table.btnFormatter'),
            Column('Löschen', 'delete_link', formatter='table.btnFormatter')
        ], **kw)

        self.user_id = user_id

    def generate_toolbar(self):
        if self.user_id is None:
            return
        if not current_user.has_property('user_hosts_change'):
            return
        args = {
            'class': "btn btn-primary",
            'href': url_for(".host_create", user_id=self.user_id),
        }
        yield "<a {}>".format(html_params(**args))
        yield "<span class=\"glyphicon glyphicon-plus\"></span>"
        yield "Host"
        yield "</a>"


class InterfaceTable(BootstrapTable):
    """A table for displaying interfaces
    """
    def __init__(self, *a, user_id=None, **kw):
        super().__init__(*a, columns=[
            Column('Host', 'host'),
            Column('MAC', 'mac'),
            Column('IPs', 'ips'),
            Column('Editieren', 'edit_link', formatter='table.btnFormatter'),
            Column('Löschen', 'delete_link', formatter='table.btnFormatter')
        ], **kw)
        self.user_id = user_id

    def generate_toolbar(self):
        if self.user_id is None:
            return
        if not current_user.has_property('user_hosts_change'):
            return
        args = {
            'class': "btn btn-primary",
            'href': url_for(".interface_create", user_id=self.user_id),
        }
        yield "<a {}>".format(html_params(**args))
        yield "<span class=\"glyphicon glyphicon-plus\"></span>"
        yield "Interface"
        yield "</a>"


class SearchTable(BootstrapTable):
    """A table for displaying search results"""
    def __init__(self, *a, **kw):
        super().__init__(*a, columns=[
            Column('ID', 'id'),
            Column('Name', 'url', formatter='table.linkFormatter'),
            Column('Login', 'login'),
        ], **kw)
