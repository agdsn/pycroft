from flask import url_for
from pydantic import BaseModel

from web.blueprints.helpers.user import no_hosts_change
from web.table.table import (
    BootstrapTable,
    Column,
    button_toolbar,
    MultiBtnColumn,
    BtnColResponse,
)


class HostTable(BootstrapTable):
    """A table for displaying hosts
    """
    name = Column("Name")
    switch = Column("Switch")
    port = Column("SwitchPort")
    actions = MultiBtnColumn("Aktionen", hide_if=no_hosts_change, width=3)
    interfaces_table_link = Column("", hide_if=lambda: True)
    interface_create_link = Column("", hide_if=lambda: True)
    id = Column("", hide_if=lambda: True)

    def __init__(self, *a, user_id=None, **kw):
        table_args = kw.pop('table_args', {})
        table_args.setdefault('data-load-subtables', "true")
        table_args.setdefault('data-detail-view', "true")
        table_args.setdefault('data-detail-formatter', "table.hostDetailFormatter")
        table_args.setdefault('data-response-handler', "table.userHostResponseHandler")
        kw['table_args'] = table_args

        super().__init__(*a, **kw)
        self.user_id = user_id

    @property
    def toolbar(self):
        if self.user_id is None:
            return
        if no_hosts_change():
            return

        href = url_for("host.host_create", user_id=self.user_id)
        return button_toolbar("Host", href)


class HostRow(BaseModel):
    name: str | None
    switch: str | None
    port: str | None
    actions: list[BtnColResponse]
    interfaces_table_link: str
    interface_create_link: str
    id: int


class InterfaceTable(BootstrapTable):
    """A table for displaying interfaces
    """
    name = Column("Name")
    mac = Column("MAC")
    ips = Column("IPs")
    actions = MultiBtnColumn("Aktionen", hide_if=no_hosts_change)

    def __init__(self, *a, host_id=None, **kw):
        table_args = kw.pop('table_args', {})
        table_args.setdefault('data-hide-pagination-info', "true")
        table_args.setdefault('data-search', "false")
        kw['table_args'] = table_args

        super().__init__(*a, **kw)
        self.host_id = host_id


class InterfaceRow(BaseModel):
    id: int  # TODO is this used?
    host: str | None
    name: str | None
    mac: str
    ips: str
    actions: list[BtnColResponse]
