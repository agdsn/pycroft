from flask import url_for

from bs_table_py.table import BootstrapTable, Column, \
    LinkColumn, button_toolbar, MultiBtnColumn, DateColumn
from web.blueprints.helpers.user import no_membership_change


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
    created_at = DateColumn("Erstellt um", width=2)
    type_ = Column("Logtyp", name='type', sortable=False)
    user = Column("Nutzer", formatter='table.userFormatter')
    message = Column("Nachricht")


class LogTableSpecific(RefreshableTableMixin, BootstrapTable):
    """A table for displaying logs"""
    created_at = DateColumn("Erstellt um", width=2)
    user = Column("Nutzer", formatter='table.userFormatter')
    message = Column("Nachricht")


class MembershipTable(BootstrapTable):
    """A table for displaying memberships

    In the toolbar, a “new membership” button is inserted if the
    :py:obj:`current_user` has the ``add_membership`` property.
    """
    group_name = Column("Gruppe")
    begins_at = DateColumn("Beginn")
    ends_at = DateColumn("Ende")
    actions = MultiBtnColumn("Aktionen", hide_if=no_membership_change)

    def __init__(self, *a, user_id=None, **kw):
        super().__init__(*a, **kw)
        self.user_id = user_id

    @property
    def toolbar(self):
        if self.user_id is None:
            return
        if no_membership_change():
            return

        href = url_for(".add_membership", user_id=self.user_id)
        return button_toolbar("Mitgliedschaft", href)

    class Meta:
        table_args = {
            'data-row-attributes': 'table.membershipRowAttributes',
            'data-row-style': 'table.membershipRowFormatter',
            'class': 'membership-table'
        }


class SearchTable(BootstrapTable):
    """A table for displaying search results"""
    id = Column("ID")
    url = LinkColumn("Name")
    login = Column("Login")


class TrafficTopTable(BootstrapTable):
    """A table for displaying the users with the highest traffic usage"""
    url = LinkColumn("Name")
    traffic_for_days = Column("Traffic", formatter='table.byteFormatterBinary')


class RoomHistoryTable(BootstrapTable):
    room = LinkColumn("Wohnort")
    begins_at = DateColumn("Von")
    ends_at = DateColumn("Bis")


class PreMemberTable(BootstrapTable):
    name = Column("Name")
    login = Column("Login")
    email = Column("Email")
    email_confirmed = Column("✓")
    move_in_date = DateColumn("Einzug am")
    actions = MultiBtnColumn("Aktionen", hide_if=no_membership_change)
