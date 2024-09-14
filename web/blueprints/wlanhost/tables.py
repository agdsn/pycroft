#  Copyright (c) 2024. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
import typing as t

from flask import url_for
from pydantic import BaseModel

from web.blueprints.helpers.user import no_hosts_change
from web.table.lazy_join import HasDunderStr
from web.table.table import (
    BootstrapTable,
    Column,
    button_toolbar,
    MultiBtnColumn,
    BtnColResponse,
    MultiLinkColumn,
    LinkColResponse,
)

class HostRow(BaseModel):
    name: str | None = None
    actions: list[BtnColResponse]
    interfaces_table_link: str
    interface_create_link: str
    id: int


class WlanHostTable(BootstrapTable):
    """A table for displaying hosts
    """
    name = Column("Name")
    interface_create_link = Column("Mac")
    actions = MultiBtnColumn("Aktionen", hide_if=no_hosts_change, width=3)
    #interfaces_table_link = Column("", hide_if=lambda: True)

    id = Column("", hide_if=lambda: True)

    def __init__(self, *, user_id: int | None = None, **kw: t.Any) -> None:
        table_args = kw.pop('table_args', {})
        table_args.setdefault('data-load-subtables', "true")
        table_args.setdefault('data-detail-view', "true")
        table_args.setdefault('data-detail-formatter', "table.hostDetailFormatter")
        table_args.setdefault('data-response-handler', "table.userHostResponseHandler")
        kw['table_args'] = table_args

        super().__init__(**kw)
        self.user_id = user_id

    @property
    def toolbar(self) -> HasDunderStr | None:
        if self.user_id is None:
            return None
        if no_hosts_change():
            return None

        href = url_for("wlan-host.host_create", user_id=self.user_id)
        return button_toolbar("Host", href)
