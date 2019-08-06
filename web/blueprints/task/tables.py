from web.blueprints.helpers.table import BootstrapTable, Column, DateColumn, \
    MultiBtnColumn, LinkColumn
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

    def __init__(self, hidden_columns=[], *a, **kw):
        table_args = kw.pop('table_args', {})
        table_args.setdefault('data-detail-view', "true")
        table_args.setdefault('data-sort-name', "due")
        table_args.setdefault('data-sort-order', "desc")
        table_args.setdefault('data-row-style', "table.taskRowFormatter")
        table_args.setdefault('data-detail-formatter',
                              "table.taskDetailFormatter")

        if 'user' in hidden_columns:
            self.user.hide_if = lambda: True
        else:
            self.user.hide_if = lambda: False

        kw['table_args'] = table_args

        super().__init__(*a, **kw)
