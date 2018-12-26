from collections import OrderedDict
from copy import copy
from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Dict, Iterable, Tuple, Any, FrozenSet

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

    def __init__(self, title, name=None, formatter=None, width=0,
                 cell_style=None, col_args=None):
        self.name = name
        self.title = title
        self.formatter = formatter if formatter is not None else False
        self.cell_style = cell_style if cell_style is not None else False
        self.width = width
        self.col_args = col_args if col_args is not None else {}

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
        html_args.update(self.col_args)
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


UnboundTableArgs = FrozenSet[Tuple[str, Any]]
TableArgs = Dict[str, str]


def _infer_table_args(meta_obj, superclass_table_args: TableArgs) -> UnboundTableArgs:
    args = {}
    args.update(**superclass_table_args)
    if meta_obj:
        args.update(**getattr(meta_obj, 'table_args', {}))

    return frozenset(args.items())


class BootstrapTableMeta(type):
    """Provides a list of all attribute names bound to columns.

    In particular, this metaclass provides the following properties:
    - :py:attr:`column_attrname_map`
    - :py:attr:`_table_args`
    """
    def __new__(mcls, name, bases, dct: Dict[str, Any]):
        meta = dct.pop('Meta', None)
        cls = super().__new__(mcls, name, bases, dct)

        old_table_args = dict(getattr(cls, '_table_args', {}))
        # the type is frozenset for immutability
        cls._table_args = _infer_table_args(meta, old_table_args)

        # we need to copy: else we would reference the superclass's
        # column_attrname_map and update it as well
        new_col_attr_map = copy(getattr(cls, 'column_attrname_map', OrderedDict()))

        for attrname, new_col in dct.items():
            if isinstance(new_col, Column):
                if not hasattr(new_col, 'name') or not new_col.name:
                    new_col.name = attrname
                new_col_attr_map[new_col.name] = attrname
        cls.column_attrname_map = new_col_attr_map

        return cls


class BootstrapTable(metaclass=BootstrapTableMeta):
    """An extendable, HTML-renderable bootstrap-table

    The table's HTML can be rendered using :meth:`render`.  NB:
    :meth:`__str__` and :meth:`__html__` are NOT provided, since
    :meth:`render` expects an obligatory `table_id`!

    :param data_url: The URL to be used as a JSON endpoint.  The JSON
        endpoint must provide the table data in the scheme defaulting
        to ``{"rows": [], "total": …}``.  In this instance, a custom
        response handler is used, which accesses the table contents on
        the sub-key ``items``: ``{"items": {"rows": …, "total": …}}``.
        The endpoint should also support the parameters limit, offset,
        search, sort, order to make server-side pagination work.
    :param table_args: Additional things to be passed to table_args.
    """
    column_attrname_map: Dict[str, str]  # provided by BootstrapTableMeta
    _table_args: UnboundTableArgs  # provided by BootstrapTableMeta
    table_args: TableArgs

    class Meta:
        table_args = {'data-toggle': "table"}

    def __init__(self, data_url, table_args=None):
        self.data_url = data_url
        # un-freeze the classes table args so it can be modified on the instance
        self.table_args = dict(self._table_args)
        self.table_args.setdefault('data-url', self.data_url)
        if table_args:
            self.table_args.update(table_args)

    @property
    def _columns(self) -> List[Column]:
        return [getattr(self, a) for a in self.column_attrname_map.values()]

    @property
    def columns(self):
        """Wrapper for subclasses to override."""
        return self._columns

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


@dataclass
class TableSplit:
    prefix: str
    title: str


class SplittedTable(BootstrapTable):
    """A table that repeats it columns in multiple flavors

    If you assign :py:attr:`splits` a sequence of prefix/Title tuples,
    like ``(('split_1_prefix', "Split 1 Title"), …)``, the table gets an
    additional header of the form ``Split 1 Title | _`` and represents every
    column in the :py:attr:`columns` property multiple times, each time
    equipped with the chosen prefix.

    For instance, if ``splits = (('a', "Type A"), ('b', "Type B"))``, and you
    have columns ``name, id``, the effective column list will be
    ``a_name, a_id, b_name, b_id``.
    """
    splits: Iterable[Tuple[str, str]]

    def _iter_typed_splits(self):
        for t in self.splits:
            yield TableSplit(*t)

    @property
    def columns(self):
        cols = []
        unaltered_columns = self._columns
        for split in self._iter_typed_splits():
            for c in unaltered_columns:
                prefixed_col = copy(c)
                prefixed_col.name = f"{split.prefix}_{c.name}"
                cols.append(prefixed_col)
        return cols

    def generate_table_header(self):
        yield "<thead>"
        yield "<tr>"
        for split in self._iter_typed_splits():
            yield ("<th colspan=\"{}\" class=\"text-center\">{}</th>"
                   .format(len(super().columns), split.title))
        yield "</tr>"

        yield "<tr>"  # that's the same as in BootstrapTable.
        for col in self.columns:
            yield "<th {}>{}</th>".format(
                col.build_col_args(**{'data-field': col.name}),
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
