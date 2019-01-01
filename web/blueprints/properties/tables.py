from flask import url_for
from flask_babel import gettext
from flask_login import current_user

from web.blueprints.helpers.table import BootstrapTable, Column, BtnColumn, \
    button_toolbar


def no_group_change():
    return not current_user.has_property('groups_traffic_change')


class TrafficGroupTable(BootstrapTable):
    """A table for displaying traffic groups"""
    name = Column("Bezeichnung")
    credit_amount = Column("Gutschrift")
    credit_interval = Column("Intervall")
    credit_limit = Column("Anspargrenze")
    initial_credit = Column("Initialer Credit")
    delete = BtnColumn("Löschen", hide_if=no_group_change)

    @property
    def toolbar(self):
        """A “create traffic group” button"""
        if no_group_change():
            return ""
        return button_toolbar(gettext("Neue Trafficgruppe"),
                              url_for(".traffic_group_create"))
