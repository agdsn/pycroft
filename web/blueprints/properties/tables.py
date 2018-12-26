from flask import url_for
from flask_babel import gettext

from web.blueprints.helpers.table import BootstrapTable, Column, BtnColumn, \
    button_toolbar


class TrafficGroupTable(BootstrapTable):
    """A table for displaying traffic groups"""
    name = Column("Bezeichnung")
    credit_amount = Column("Gutschrift")
    credit_interval = Column("Intervall")
    credit_limit = Column("Anspargrenze")
    initial_credit = Column("Initialer Credit")
    delete = BtnColumn("Löschen")

    @property
    def toolbar(self):
        """A “create traffic group” button"""
        return button_toolbar(gettext("Neue Trafficgruppe"),
                              url_for(".traffic_group_create"))
