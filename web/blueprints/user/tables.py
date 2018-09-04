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
            Column('created_at', 'Erstellt um', width=2),
            Column('type', 'Logtyp'),
            Column('user', 'Nutzer', formatter='table.userFormatter'),
            Column('message', 'Nachricht'),
        ], **kw)


class LogTableSpecific(RefreshableTableMixin, BootstrapTable):
    """A table for displaying logs"""
    def __init__(self, *a, **kw):
        super().__init__(*a, columns=[
            # specific tables don't need the `type`
            Column('created_at', 'Erstellt um', width=2),
            Column('user', 'Nutzer', formatter='table.userFormatter'),
            Column('message', 'Nachricht'),
        ], **kw)


class MembershipTable(BootstrapTable):
    """A table for displaying memberships

    In the toolbar, a “new membership” button is inserted if the
    :py:obj:`current_user` has the ``add_membership`` property.
    """
    def __init__(self, *a, user_id=None, **kw):
        super().__init__(*a, columns=[
            Column('group_name', 'Gruppe'),
            Column('begins_at', 'Beginn'),
            Column('ends_at', 'Ende'),
            Column('actions', 'Aktionen', formatter='table.multiBtnFormatter')
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

    It has a “change_mac” column.
    """
    def __init__(self, *a, **kw):
        super().__init__(*a, columns=[
            Column('ip', 'IP-Adresse'),
            Column('mac', 'Mac-Adresse'),
            Column('switch', 'Switch'),
            Column('port', 'Switchport'),
            Column('action', 'MAC ändern', formatter='table.btnFormatter')
        ], **kw)


class SearchTable(BootstrapTable):
    """A table for displaying search results"""
    def __init__(self, *a, **kw):
        super().__init__(*a, columns=[
            Column('id', 'ID'),
            Column('url', 'Name', formatter='table.linkFormatter'),
            Column('login', 'Login'),
        ], **kw)
