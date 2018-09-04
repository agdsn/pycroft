from urllib.parse import urlparse, urlunparse, urlencode, parse_qsl

from flask import url_for
from flask_babel import gettext
from wtforms.widgets.core import html_params

from web.blueprints.helpers.table import BootstrapTable, Column

class TrafficGroupTable(BootstrapTable):
    """A table for displaying traffic groups"""
    def __init__(self, *a, **kw):
        super().__init__(*a, columns=[
            Column(name='name', title='Bezeichnung'),
            Column(name='credit_amount', title='Gutschrift'),
            Column(name='credit_interval', title='Intervall'),
            Column(name='credit_limit', title='Anspargrenze'),
            Column(name='initial_credit', title='Initialer Credit'),
            Column(name='delete', title='Löschen', formatter='table.btnFormatter'),
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
