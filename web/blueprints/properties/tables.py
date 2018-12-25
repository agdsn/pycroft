from urllib.parse import urlparse, urlunparse, urlencode, parse_qsl

from flask import url_for
from flask_babel import gettext
from wtforms.widgets.core import html_params

from web.blueprints.helpers.table import BootstrapTable, Column

class TrafficGroupTable(BootstrapTable):
    """A table for displaying traffic groups"""
    def __init__(self, *a, **kw):
        super().__init__(*a, columns=[
            Column(title='Bezeichnung', name='name'),
            Column(title='Gutschrift', name='credit_amount'),
            Column(title='Intervall', name='credit_interval'),
            Column(title='Anspargrenze', name='credit_limit'),
            Column(title='Initialer Credit', name='initial_credit'),
            Column(title='Löschen', name='delete',
                   formatter='table.btnFormatter'),
        ], **kw)

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
