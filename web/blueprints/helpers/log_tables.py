#  Copyright (c) 2023. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details

import typing as t

from pydantic import BaseModel

from web.table.table import (
    BootstrapTable,
    RelativeDateColumn,
    Column,
    UserColumn,
    DateColResponse,
    UserColResponse,
)


class RefreshableTableMixin:
    """A mixin class showing the refresh button by default.

    In :py:meth:`__init__`s ``table_args`` argument, a default of
    ``{'data-show-refresh': "true"}`` is established.
    """

    def __init__(self, *a, **kw) -> None:
        table_args = kw.pop("table_args", {})
        table_args.setdefault("data-show-refresh", "true")
        kw["table_args"] = table_args
        super().__init__(*a, **kw)


class LogTableExtended(RefreshableTableMixin, BootstrapTable):
    """A table for displaying logs, with a ``type`` column"""

    created_at = RelativeDateColumn("Erstellt um", width=2)
    type_ = Column("Logtyp", name="type", sortable=False)
    user = UserColumn("Nutzer")
    message = Column("Nachricht", formatter="table.withMagicLinksFormatter")


class LogTableSpecific(RefreshableTableMixin, BootstrapTable):
    """A table for displaying logs"""

    created_at = RelativeDateColumn("Erstellt um", width=2)
    user = UserColumn("Nutzer")
    message = Column("Nachricht", formatter="table.withMagicLinksFormatter")


LogType = t.Literal["user", "room", "hades", "task", "all"]
LOG_TYPES = frozenset(t.get_args(LogType))


def is_log_type(type: str) -> t.TypeGuard[LogType]:
    return type in LOG_TYPES


class LogTableRow(BaseModel):
    created_at: DateColResponse
    type: LogType | None = None
    user: UserColResponse
    message: str
