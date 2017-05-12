from jinja2 import Markup
from wtforms.widgets.core import html_params

class Column:
    def __init__(self, name, title, formatter=None, width=0):
        self.name = name
        self.title = title
        self.formatter = formatter
        self.width = width


class BootstrapTable:
    def __init__(self, columns, data_url, row_style=False,
                 server_pagination=False, sort_order='asc'):
        self.columns = columns
        self.data_url = data_url
        self.row_style = row_style
        self.server_pagination = server_pagination
        self.sort_order = sort_order

    def render(self, table_id):
        # NB: in html_args, setting an argument to `False` makes it
        # disappear.
        html = []

        toolbar_args = html_params(id="{}-toolbar".format(table_id),
                                   class_="table table_striped",
                                   role="toolbar")
        html.append("<div {}></div>".format(toolbar_args))

        table_args = {
            'id': table_id,
            'class': "table table-striped",
            'data-page-size': 20,
            'data-toggle': "table",
            'data-cache': "false",
            'data-url': self.data_url,
            'data-response-handler': "responseHandler",
            'data-search': "true",
            'data-sort-order': self.sort_order,
            'data-side-pagination': "server" if self.server_pagination else False,
            'data-pagination': "true",
            'data-row-style': self.row_style,  # default False
            'data-toolbar': "#{}-toolbar".format(table_id),
        }

        html.append("<table {}>".format(html_params(**table_args)))
        html.append("<thead>")
        html.append("<tr>")
        for col in self.columns:
            th_args = {
                'class': "col-sm-{}".format(col.width) if col.width else False,
                'data-sortable': "true",
                'data-field': col.name,
                'data-formatter': col.formatter if col.formatter is not None else False,
            }
            html.append("<th {}>{}</th>".format(html_params(**th_args), col.title))

        html.append("</tr>")
        html.append("</thead>")
        html.append("</table>")
        return Markup("\n".join(html))


"""
    <div id="{{ table_id }}-toolbar" class="btn-toolbar" role="toolbar">
        {% if caller is defined %}
            {{ caller() }}
        {% endif %}
    </div>
    <table id="{{ table_id }}" class="table table-striped"
           data-page-size=20
           data-toggle="table"
           data-cache="false"
           {% if data_url %}data-url="{{ data_url }}"{% endif %}
           data-response-handler="responseHandler"
           data-search="true"
           data-sort-order="{{ sort_order }}"
           {% if server_pagination %}data-side-pagination="server"{% endif %}
           data-pagination="true"
           {% if row_style %}data-row-style="{{ row_style }}"{% endif %}
           data-toolbar="#{{ table_id }}-toolbar">
        <thead>
        <tr>
            {% for col in display_columns %}
                {# The formatter given as `col.formatter` determines
                the parsing.  A function of this name must be
                available in the document the table is built into. #}
                <th data-sortable="true" data-field="{{ col.name }}"
                    {% if col.formatter is defined %}data-formatter="{{ col.formatter }}"{% endif %}
                    {% if col.width is defined %}class="col-sm-{{ col. width }}"{% endif %}
                >{{ col.title }}</th>
            {% endfor %}
        </tr>
        </thead>
        {% if footer is defined %}<tfoot><tr>{% for footcol in footer %}
            <td{% if footcol.colspan is defined and footcol.colspan > 0 %} colspan="{{ footcol.colspan }}"{% endif %}>{{ footcol.title }}</td>
        {% endfor %}</tr></tfoot>{% endif %}
    </table>
"""
