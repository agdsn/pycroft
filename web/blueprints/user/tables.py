import typing

from flask import url_for
from pydantic import BaseModel

from web.blueprints.helpers.log_tables import RefreshableTableMixin
from web.table.lazy_join import HasDunderStr
from web.table.table import (
    BootstrapTable,
    Column,
    LinkColumn,
    button_toolbar,
    MultiBtnColumn,
    DateColumn,
    TextWithBooleanColumn,
    LinkColResponse,
    DateColResponse,
    BtnColResponse,
)
from web.blueprints.helpers.user import no_membership_change


class MembershipTable(BootstrapTable):
    """A table for displaying memberships

    In the toolbar, a “new membership” button is inserted if the
    :py:obj:`current_user` has the ``add_membership`` property.
    """
    group_name = Column("Gruppe")
    begins_at = DateColumn("Beginn")
    ends_at = DateColumn("Ende")
    actions = MultiBtnColumn("Aktionen", hide_if=no_membership_change)

    def __init__(self, *a, user_id: int | None = None, **kw) -> None:
        super().__init__(*a, **kw)
        self.user_id = user_id

    @property
    def toolbar(self) -> HasDunderStr | None:
        if self.user_id is None:
            return None
        if no_membership_change():
            return None

        href = url_for(".add_membership", user_id=self.user_id)
        return button_toolbar("Mitgliedschaft", href)

    class Meta:
        table_args = {
            'data-row-attributes': 'table.membershipRowAttributes',
            'data-row-style': 'table.membershipRowFormatter',
            'class': 'membership-table'
        }


class MembershipRow(BaseModel):
    group_name: str
    begins_at: DateColResponse
    ends_at: DateColResponse
    actions: list[BtnColResponse]
    # used by membershipRowAttributes
    grants: list[str | None]
    denies: list[str | None]
    # used by membershipRowFormatter
    active: bool


class SearchTable(BootstrapTable):
    """A table for displaying search results"""
    id = Column("ID")
    url = LinkColumn("Name")
    login = Column("Login")


class UserSearchRow(BaseModel):
    """note: contains more columns than just the response for the table.

    specific search and quick search are actually different concerns,
    but noone has separated this yet.
    """

    id: int
    name: str
    url: LinkColResponse
    login: str
    room_id: int | None = None


class TrafficTopTable(BootstrapTable):
    """A table for displaying the users with the highest traffic usage"""
    url = LinkColumn("Name")
    traffic_for_days = Column("Traffic", formatter='table.byteFormatterBinary')


class TrafficTopRow(BaseModel):
    id: int
    name: str
    traffic_for_days: int
    url: LinkColResponse


class RoomHistoryTable(BootstrapTable):
    room = LinkColumn("Wohnort")
    begins_at = DateColumn("Von")
    ends_at = DateColumn("Bis")


class RoomHistoryRow(BaseModel):
    room: LinkColResponse
    begins_at: DateColResponse
    ends_at: DateColResponse


class TenancyTable(BootstrapTable):
    room = LinkColumn("Zimmer")
    begins_at = DateColumn("Von")
    ends_at = DateColumn("Bis")
    status = Column("Status")


class TenancyRow(BaseModel):
    room: LinkColResponse
    begins_at: DateColResponse
    ends_at: DateColResponse
    status: str


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


class TextWithBooleanColResponse(BaseModel):
    text: str
    bool: bool
    icon_true: str | None = None
    icon_false: str | None = None


class PreMemberRow(BaseModel):
    prm_id: int | str
    name: TextWithBooleanColResponse
    login: str
    email: TextWithBooleanColResponse
    # email_confirmed?
    move_in_date: DateColResponse
    actions: list[BtnColResponse]
    action_required: bool  # used by membershipRequestRowFormatter


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
        def row(  # type: ignore[override]
            cls,
            id: int,
            user: dict,
            room_shortname: dict,
            current_properties: str,
            num_hosts: int,
            end_of_membership: dict,
        ) -> dict:
            ...


class ArchivableMemberRow(BaseModel):
    id: int
    user: LinkColResponse
    room_shortname: LinkColResponse | None = None
    num_hosts: int
    current_properties: str
    end_of_membership: DateColResponse
