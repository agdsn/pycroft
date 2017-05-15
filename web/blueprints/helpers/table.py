from jinja2 import Markup
from wtforms.widgets.core import html_params

class Column:
    def __init__(self, name, title, formatter=None, width=0):
        self.name = name
        self.title = title
        self.formatter = formatter if formatter is not None else False
        self.width = width

    def build_col_args(self, **kwargs):
        html_args = {
            'class': "col-sm-{}".format(self.width) if self.width else False,
            'data-sortable': "true",
            'data-field': self.name,
            'data-formatter': self.formatter,
        }
        html_args.update(kwargs)
        return html_params(**html_args)


class BootstrapTable:
    def __init__(self, columns, data_url, table_args=None):
        self.columns = columns
        self.data_url = data_url
        self.table_args = table_args if table_args is not None else {}
        self._init_table_args()

    def _init_table_args(self):
        default_args = {
            'class': "table table-striped",
            'data-page-size': 20,
            'data-toggle': "table",
            'data-cache': "false",
            'data-url': self.data_url,
            'data-response-handler': "responseHandler",
            'data-search': "true",
            'data-pagination': "true",
        }
        for key, val in default_args.items():
            self.table_args.setdefault(key, val)

    def generate_table_header(self):
        yield "<thead>"
        yield "<tr>"
        for col in self.columns:
            yield "<th {}>{}</th>".format(col.build_col_args(), col.title)
        yield "</tr>"
        yield "</thead>"

    def render(self, table_id):
        # NB: in html_args, setting an argument to `False` makes it
        # disappear.
        html = []

        toolbar_args = html_params(id="{}-toolbar".format(table_id),
                                   class_="table table_striped",
                                   role="toolbar")
        html.append("<div {}></div>".format(toolbar_args))

        table_args = self.table_args
        table_args.update({
            'id': table_id,
            'data-toolbar': "#{}-toolbar".format(table_id),
        })

        html.append("<table {}>".format(html_params(**table_args)))
        html += list(self.generate_table_header())
        html.append("</table>")

        return Markup("\n".join(html))


class SplittedTable(BootstrapTable):
    def __init__(self, *a, splits, **kw):
        """Initialize a new Splitted Table

        :param splits: Split definitions of the format
            (('split_1_prefix', "Display_Name"), …).  The format will
            be checked
        :param kwargs: Passed to super()
        """
        super().__init__(*a, **kw)
        # each split shall have the format:
        # ('split_prefix', "Name to be displayed")
        if any(len(x) != 2 for x in splits):
            raise ValueError("`splits` must be a tuple of 2-tuples")
        self.splits = splits

    def generate_table_header(self):
        yield "<thead>"
        yield "<tr>"
        for _, split_name in self.splits:
            yield ("<th colspan=\"{}\" class=\"text-center\">{}</th>"
                   .format(len(self.columns), split_name))
        yield "</tr>"

        yield "<tr>"
        def prefixed_col(prefix, col_name):
            return "{prefix}_{col_name}".format(prefix=prefix, col_name=col_name)
        for split_prefix, _ in self.splits:
            for col in self.columns:
                new_name = prefixed_col(split_prefix, col.name)
                yield "<th {}>{}</th>".format(col.build_col_args(data_field=new_name),
                                              col.title)
        yield "</tr>"
        yield "</thead>"
