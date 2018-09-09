from datetime import date, datetime

from jinja2 import Markup
from wtforms.widgets.core import html_params

from pycroft.helpers import utc
from web.template_filters import date_filter, datetime_filter

class Column:
    """A class representing a bootstrap-table column

    This class bundles all the attributes commonly needed to represent
    a table column as used in a bootstrap-table.  It defines a method
    :py:meth:`build_col_args` for building the args needed in the
    corresponding ``<td>`` element for the table header.

    For documentation concerning bootstrap-tables in general, see
    http://bootstrap-table.wenzhixin.net.cn/documentation/

    :param name: The name of the column.  This must coincide with the
        key given in the JSON endpoint's response, e.g. if this
        column's name is ``user_id``, the response JSON has to be of
        the form ``{"items": [{"user_id": value, …}, …]}``.
    :param title: The title to be displayed in the column header.
    :param formatter: An optional formatter to use.  The referenced
        value must be available as a javascript function for the
        column's value parsing to work properly.  See the
        ``data-formatter`` attribute in the bootstrap-table docs for
        details.
    :param width: An optional width, being translated to the
        ``col-sm-{width}`` bootstrap class.
    :param cell_style: Similar to :param:`formatter`, an optional
        javascript function's name to be passed to
        ``data-cell-style``.
    """
    def __init__(self, name, title, formatter=None, width=0, cell_style=None):
        self.name = name
        self.title = title
        self.formatter = formatter if formatter is not None else False
        self.cell_style = cell_style if cell_style is not None else False
        self.width = width

    def __repr__(self):
        return "<{cls} {name!r} title={title!r}>".format(
            cls=type(self).__name__,
            name=self.name,
            title=self.title,
        )

    def build_col_args(self, **kwargs):
        """Build th html-style attribute string for this column.

        This string can be used to add this column to a table in the
        header: ``"<td {}></td>".format(col.build_col_args())``.
        Attributes are utilized as described in :meth:`__init__`.

        :param kwargs: Keyword arguments which are merged into the
            dict of html attributes.
        """
        html_args = {
            'class': "col-sm-{}".format(self.width) if self.width else False,
            'data-sortable': "true",
            'data-field': self.name,
            'data-formatter': self.formatter,
            'data-cell-style': self.cell_style,
        }
        html_args.update(kwargs)
        return html_params(**html_args)

    def render(self):
        """Render this column as a ``<th>`` html tag.

        This uses the arguments provided by :meth:`build_col_args` and
        the :attr:`title` for the inner HTML.
        """
        return "<th {}>{}</th>".format(self.build_col_args(), self.title)

    __str__ = render
    __html__ = render


class BootstrapTable:
    """An extendable, HTML-renderable bootstrap-table

    The table's HTML can be rendered using :meth:`render`.  NB:
    :meth:`__str__` and :meth:`__html__` are NOT provided, since
    :meth:`render` expects an obligatory `table_id`!

    :param columns: A list of :py:cls:`Column` objects defining the
        columns.
    :param data_url: The URL to be used as a JSON endpoint.  The JSON
        endpoint must provide the table data in the scheme defaulting
        to ``{"rows": [], "total": …}``.  In this instance, a custom
        response handler is used, which accesses the table contents on
        the sub-key ``items``: ``{"items": {"rows": …, "total": …}}``.
        The endpoint should also support the parameters limit, offset,
        search, sort, order to make server-side pagination work.
    :param table_args: Additional things to be passed to table_args.
    """
    def __init__(self, columns, data_url, table_args=None):
        self.columns = columns
        self.data_url = data_url
        self.table_args = table_args if table_args is not None else {}
        self._init_table_args()

    def __repr__(self):
        return "<{cls} cols={numcols} data_url={data_url!r}>".format(
            cls=type(self).__name__,
            numcols=len(self.columns),
            data_url=self.data_url,
        )

    def _init_table_args(self):
        """Set the defaults of :py:attr:`table_args`"""
        default_args = {
            'data-toggle': "table",
            'data-url': self.data_url,
        }
        for key, val in default_args.items():
            self.table_args.setdefault(key, val)

    def generate_table_header(self):
        """Generate the table header from :py:attr:`columns`.

        :rtype: generator
        """
        yield "<thead>"
        yield "<tr>"
        for col in self.columns:
            yield str(col)
        yield "</tr>"
        yield "</thead>"

    @staticmethod
    def generate_toolbar():
        """Return an empty iterator.

        Used to generate the inner HTML contents of the toolbar.

        :rtype: iterator
        """
        return iter(())

    @staticmethod
    def generate_table_footer():
        """Return an empty iterator.

        Used to generate the outer HTML contents of the footer.  Must
        yield the ``<tfoot>`` tag as well.

        :rtype: iterator
        """
        return iter(())

    def render(self, table_id):
        """Render the table
        """
        # NB: in html_args, setting an argument to `False` makes it
        # disappear.
        html = []

        toolbar_args = html_params(id="{}-toolbar".format(table_id),
                                   class_="btn-toolbar",
                                   role="toolbar")
        html.append("<div {}>".format(toolbar_args))
        html += list(self.generate_toolbar())
        html.append("</div>")

        table_args = self.table_args
        table_args.update({
            'id': table_id,
            'data-toolbar': "#{}-toolbar".format(table_id),
        })

        html.append("<table {}>".format(html_params(**table_args)))
        html += list(self.generate_table_header())
        html += list(self.generate_table_footer())
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
                yield "<th {}>{}</th>".format(
                    col.build_col_args(**{'data-field': new_name}),
                    col.title
                )
        yield "</tr>"
        yield "</thead>"


def date_format(dt, default=None):
    """
    Format date or datetime objects for `table.dateFormatter`.
    :param datetime|date|None dt: a date or datetime object or None
    :param str|None default: formatted value to use if `dt` is None
    :return:
    """
    if dt is not None:
        return {
            'formatted': date_filter(dt),
            'timestamp': int(datetime.combine(dt, utc.time_min()).timestamp()),
        }
    else:
        return {
            'formatted': default if default is not None else date_filter(None),
            'timestamp': None,
        }


def datetime_format(dt, default=None):
    """
    Format datetime objects for `table.dateFormatter`.
    :param datetime|None dt: a datetime object or None
    :param str|None default: formatted value to use if `dt` is None
    :return:
    """
    if dt is not None:
        return {
            'formatted': datetime_filter(dt),
            'timestamp': int(dt.timestamp()),
        }
    else:
        return {
            'formatted': default if default is not None else datetime_filter(None),
            'timestamp': None,
        }
