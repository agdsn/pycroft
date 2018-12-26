from urllib.parse import urlparse, urlunparse, urlencode, parse_qsl

from flask import url_for
from flask_babel import gettext
from wtforms.widgets.core import html_params

from web.blueprints.helpers.table import BootstrapTable, Column, BtnColumn


class TrafficGroupTable(BootstrapTable):
    """A table for displaying traffic groups"""
    name = Column("Bezeichnung")
    credit_amount = Column("Gutschrift")
    credit_interval = Column("Intervall")
    credit_limit = Column("Anspargrenze")
    initial_credit = Column("Initialer Credit")
    delete = BtnColumn("Löschen")

    def generate_toolbar(self):
        """A “create traffic group” button"""
        args = {
            'class': "btn btn-primary",
            'href': url_for(".traffic_group_create")
        }
        yield "<a {}>".format(html_params(**args))
        yield "<span class=\"glyphicon glyphicon-plus\"></span>"
        yield gettext("Neue Trafficgruppe")
        yield "</a>"
