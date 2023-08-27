import typing as t
from pydantic import BaseModel

from web.table.table import (
    BootstrapTable,
    Column,
    DateColumn,
    MultiBtnColumn,
    LinkColumn,
    LinkColResponse,
    DateColResponse,
    BtnColResponse,
)
from web.blueprints.helpers.user import no_membership_change


class TaskTable(BootstrapTable):
    """A table for displaying tasks

    """
    user = LinkColumn("User")
    name = Column("Name")
    due = DateColumn("Datum")
    creator = LinkColumn("Ersteller")
    status = Column("Status")
    actions = MultiBtnColumn("Aktionen", hide_if=no_membership_change)
    created = Column(title=None, hide_if=lambda: True)
    parameters = Column(title=None, hide_if=lambda: True)
    exception_message = Column(title=None, hide_if=lambda: True)
    type = Column("Typ", hide_if=lambda: True)

    def __init__(
        self,
        *,
        hidden_columns: t.Container[str] = None,
        sort_order: str = "asc",
        **kw: t.Any
    ):
        table_args = kw.pop("table_args", {})
        table_args.setdefault("data-detail-view", "true")
        table_args.setdefault("data-sort-name", "due")
        table_args.setdefault("data-sort-order", sort_order)
        table_args.setdefault("data-row-style", "table.taskRowFormatter")
        table_args.setdefault("data-detail-formatter", "table.taskDetailFormatter")

        if hidden_columns and "user" in hidden_columns:
            self.user.hide_if = lambda: True
        else:
            self.user.hide_if = lambda: False

        kw['table_args'] = table_args

        super().__init__(**kw)


class TaskRow(BaseModel):
    id: int  # seems unused, not sure
    user: LinkColResponse
    name: str
    type: str
    due: DateColResponse
    creator: LinkColResponse
    status: str  # used by taskRowFormatter
    actions: list[BtnColResponse]
    created: str
    parameters: dict[str, t.Any]
    errors: list[str]  # used by taskDetailFormatter
