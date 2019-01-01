from flask import url_for
from flask_login import current_user

from web.blueprints.helpers.table import BootstrapTable, Column, BtnColumn, \
    LinkColumn, button_toolbar, MultiBtnColumn, DateColumn


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


def no_membership_change():
    return not current_user.has_property('groups_change_membership')


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


def no_userhost_change():
    return not current_user.has_property('user_hosts_change')


class HostTable(BootstrapTable):
    """A table for displaying hosts
    """
    name = Column("Name")
    switch = Column("Switch")
    port = Column("SwitchPort")
    edit_link = BtnColumn("Editieren", hide_if=no_userhost_change)
    delete_link = BtnColumn("Löschen", hide_if=no_userhost_change)

    def __init__(self, *a, user_id=None, **kw):
        super().__init__(*a, **kw)
        self.user_id = user_id

    @property
    def toolbar(self):
        if self.user_id is None:
            return
        if no_userhost_change():
            return

        href = url_for(".host_create", user_id=self.user_id)
        return button_toolbar("Host", href)


class InterfaceTable(BootstrapTable):
    """A table for displaying interfaces
    """
    host = Column("Host")
    mac = Column("MAC")
    ips = Column("IPs")
    edit_link = BtnColumn("Editieren", hide_if=no_userhost_change)
    delete_link = BtnColumn("Löschen", hide_if=no_userhost_change)

    def __init__(self, *a, user_id=None, **kw):
        super().__init__(*a, **kw)
        self.user_id = user_id

    @property
    def toolbar(self):
        if self.user_id is None:
            return
        if no_userhost_change():
            return

        href = url_for(".interface_create", user_id=self.user_id)
        return button_toolbar("Interface", href)


class SearchTable(BootstrapTable):
    """A table for displaying search results"""
    id = Column("ID")
    url = LinkColumn("Name")
    login = Column("Login")
