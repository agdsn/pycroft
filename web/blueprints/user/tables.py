import typing

from flask import url_for

from web.table.table import BootstrapTable, Column, \
    LinkColumn, button_toolbar, MultiBtnColumn, DateColumn, RelativeDateColumn, \
    custom_formatter_column, DictValueMixin, TextWithBooleanColumn
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


@custom_formatter_column('table.userFormatter')
class UserColumn(Column):
    @classmethod
    def value_plain(cls, title: str) -> dict:
        return DictValueMixin.value(type='plain', title=title)

    @classmethod
    def value_native(cls, href: str, title: str,
                     glyphicon: typing.Optional[str] = None) -> dict:
        return DictValueMixin.value(
            type='native', href=href, title=title, glyphicon=glyphicon,
        )


class LogTableExtended(RefreshableTableMixin, BootstrapTable):
    """A table for displaying logs, with a ``type`` column"""
    created_at = RelativeDateColumn("Erstellt um", width=2)
    type_ = Column("Logtyp", name='type', sortable=False)
    user = UserColumn("Nutzer")
    message = Column("Nachricht", formatter='table.withMagicLinksFormatter')


class LogTableSpecific(RefreshableTableMixin, BootstrapTable):
    """A table for displaying logs"""
    created_at = RelativeDateColumn("Erstellt um", width=2)
    user = UserColumn("Nutzer")
    message = Column("Nachricht", formatter='table.withMagicLinksFormatter')


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


class TenancyTable(BootstrapTable):
    room = LinkColumn("Zimmer")
    begins_at = DateColumn("Von")
    ends_at = DateColumn("Bis")
    status = Column("Status")


class PreMemberTable(BootstrapTable):
    prm_id = Column("ID")
    name = TextWithBooleanColumn("Name")
    login = Column("Login")
    email = TextWithBooleanColumn("E-Mail Adresse")
    move_in_date = DateColumn("Einzug am")
    actions = MultiBtnColumn("Aktionen", hide_if=no_membership_change, width=1)

    class Meta:
        table_args = {
            'data-row-style': 'table.membershipRequestRowFormatter',
        }


class ArchivableMembersTable(RefreshableTableMixin, BootstrapTable):
    class Meta:
        table_args = {'data-escape': 'false', 'data-sort-stable': True}

    id = Column("#")
    user = LinkColumn("Mitglied")
    room_shortname = LinkColumn("<i class=\"fas fa-home\"></i>")
    num_hosts = Column("<i class=\"fas fa-laptop\"></i>")
    current_properties = Column("Props", formatter="table.propertiesFormatter")
    end_of_membership = DateColumn("EOM")

    if typing.TYPE_CHECKING:
        @classmethod
        def row(cls, id: int, user: dict, room_shortname: dict,
                current_properties: str,
                num_hosts: int, end_of_membership: dict) -> dict: ...

