from __future__ import annotations
import html
import typing
import typing as t
from collections import OrderedDict
from copy import copy
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from operator import methodcaller
from typing import Iterable, Any, Callable
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

from annotated_types import Predicate
from markupsafe import Markup
from pydantic import BaseModel, Field

from .lazy_join import lazy_join, HasDunderStr


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
    :param hide_if: When this callable returns true, the column returns
        an empty string when rendered.
    :param escape: sets `data-escape`.
        Should be set to ``False`` if you use a formatter expecting something other than a string,
        because ``bootstrap-table``s builtin escaper forcefully casts to string otherwise.
    """

    def __init__(
        self,
        title: str,
        name: str | None = None,
        formatter: str | None = None,
        width: int | None = 0,
        cell_style: str | None = None,
        col_args: dict[str, str] | None = None,
        sortable: bool = True,
        hide_if: Callable[[], bool] | None = lambda: False,
        escape: bool | None = None,
    ) -> None:
        self.name = name
        self.title = title
        self.formatter = formatter if formatter is not None else False
        self.cell_style = cell_style if cell_style is not None else False
        self.width = width
        self.col_args = col_args if col_args is not None else {}
        if escape is not None:
            self.col_args['data-escape'] = "true" if escape else "false"
        self.sortable = sortable
        self.hide_if = hide_if

    def __repr__(self) -> str:
        return "<{cls} {name!r} title={title!r}>".format(
            cls=type(self).__name__,
            name=self.name,
            title=self.title,
        )

    def build_col_args(self, **kwargs: HtmlParamValue) -> str:
        """Build th html-style attribute string for this column.

        This string can be used to add this column to a table in the
        header: ``f"<td {col.build_col_args()}></td>"``.
        Attributes are utilized as described in :meth:`__init__`.

        :param kwargs: Keyword arguments which are merged into the
            dict of html attributes.
        """
        html_args: dict[str, HtmlParamValue] = {
            'class': f"col-sm-{self.width}" if self.width else False,
            'data-sortable': "true" if self.sortable else "false",
            'data-field': self.name,
            'data-formatter': self.formatter,
            'data-cell-style': self.cell_style,
        }
        html_args.update(self.col_args)
        html_args.update(kwargs)
        return html_params(**html_args)

    def render(self) -> str:
        """Render this column as a ``<th>`` html tag.

        This uses the arguments provided by :meth:`build_col_args` and
        the :attr:`title` for the inner HTML.
        """
        if self.hide_if():
            return ""
        return f"<th {self.build_col_args()}>{self.title}</th>"

    __str__ = render
    __html__ = render




_T = t.TypeVar("_T", bound=Column)
_TT: t.TypeAlias = type[_T]

# noinspection PyPep8Naming
class custom_formatter_column:
    def __init__(self, formatter_name: str) -> None:
        self.formatter_name = formatter_name

    def __call__(self, cls: type[_T]) -> type[_T]:
        """Decorate the classes `__init__` function to inject the formatter"""
        old_init = cls.__init__

        def __init__(obj, *a, **kw):  # type: ignore[no-untyped-def]
            kw.setdefault("escape", False)
            kw.setdefault("formatter", self.formatter_name)
            old_init(obj, *a, **kw)

        cls.__init__ = __init__  # type: ignore[method-assign, assignment]
        return cls


BtnClass = t.Annotated[str, Predicate(methodcaller("startswith", "btn-"))]
IconClass = t.Annotated[str, Predicate(methodcaller("startswith", "fa-"))]


class BtnColResponse(BaseModel):
    btn_class: BtnClass | None = None
    href: str
    title: str
    tooltip: str | None = None
    new_tab: bool | None = None
    icon: IconClass | list[IconClass] | None = None


@custom_formatter_column('table.btnFormatter')
class BtnColumn(Column):
    def __init__(self, *a: t.Any, **kw: t.Any) -> None:
        if kw.pop("sortable", False):
            raise ValueError("BtnColumn does not support sorting")
        kw["sortable"] = False
        super().__init__(*a, **kw)


@custom_formatter_column('table.multiBtnFormatter')
class MultiBtnColumn(Column):
    def __init__(self, *a: t.Any, **kw: t.Any) -> None:
        kw.setdefault("sortable", False)
        super().__init__(*a, **kw)


class LinkColResponse(BaseModel):
    href: str
    title: str
    glyphicon: IconClass | None = None
    new_tab: bool | None = None


@custom_formatter_column('table.linkFormatter')
class LinkColumn(Column):
    if typing.TYPE_CHECKING:
        @classmethod
        def value(
            cls,
            *,
            href: str,
            title: str,
            glyphicon: str | None = None,
            new_tab: bool | None = None,
        ) -> dict:
            # for argument types, see `linkFormatter`
            ...



@custom_formatter_column('table.dateFormatter')
class DateColumn(Column):
    pass


class DateColResponse(BaseModel):
    """Response for pre-formatted date or datetime data"""

    formatted: str
    timestamp: int | None = None


@custom_formatter_column('table.relativeDateFormatter')
class RelativeDateColumn(Column):
    pass


RelativeDateResponse = DateColResponse


@custom_formatter_column('table.textWithBooleanFormatter')
class TextWithBooleanColumn(Column):
    pass


@custom_formatter_column('table.userFormatter')
class UserColumn(Column):
    pass


class UserColResponsePlain(BaseModel):
    type: t.Annotated[t.Literal["plain"], Field(init_var=False)] = "plain"
    title: str


class UserColResponseNative(LinkColResponse):
    type: t.Annotated[t.Literal["native"], Field(init_var=False)] = "native"


UserColResponse = UserColResponsePlain | UserColResponseNative


@custom_formatter_column('table.ibanFormatter')
class IbanColumn(Column):
    pass


UnboundTableArgs = frozenset[tuple[str, Any]]
TableArgs = dict[str, HasDunderStr]


def _infer_table_args(
    meta_obj: object, superclass_table_args: TableArgs
) -> UnboundTableArgs:
    args: TableArgs = {}
    args.update(**superclass_table_args)
    if meta_obj:
        args.update(**getattr(meta_obj, 'table_args', {}))

    return frozenset(args.items())


def _infer_enforced_url_params(
    meta_obj: object, superclass_params: dict[str, str]
) -> frozenset[tuple[str, str]]:
    params: dict[str, str] = {}
    params.update(**superclass_params)
    if meta_obj:
        params.update(**getattr(meta_obj, 'enforced_url_params', {}))

    return frozenset(params.items())


AttributeMap: t.TypeAlias = OrderedDict[str, str]
class BootstrapTableMeta(type):
    """Provides a list of all attribute names bound to columns.

    In particular, this metaclass provides the following properties:
    - :py:attr:`column_attrname_map`
    - :py:attr:`_table_args`
    """

    _table_args: UnboundTableArgs
    _enforced_url_params: frozenset[tuple[str, str]]
    column_attrname_map: OrderedDict  # TODO specify key/val types

    def __new__(
        mcls: type[BootstrapTableMeta],
        name: str,
        bases: tuple[type, ...],
        dct: dict[str, Any],
    ) -> type:
        meta = dct.pop("Meta", None)
        cls = super().__new__(mcls, name, bases, dct)

        old_table_args = dict(getattr(cls, '_table_args', {}))
        # the type is frozenset for immutability
        cls._table_args = _infer_table_args(meta, old_table_args)

        old_params: dict[str, str] = dict(getattr(cls, "_enforced_url_params", {}))
        # frozenset here as well
        cls._enforced_url_params = _infer_enforced_url_params(meta, old_params)

        # we need to copy: else we would reference the superclass's
        # column_attrname_map and update it as well
        # TODO is the cast appropriate? what if a subclass has a `column_attrname_map` of a different type?
        new_col_attr_map = copy(
            t.cast(OrderedDict, getattr(cls, "column_attrname_map", OrderedDict()))
        )

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

    column_attrname_map: OrderedDict[str, str]  # provided by BootstrapTableMeta
    _table_args: UnboundTableArgs  # provided by BootstrapTableMeta
    _enforced_url_params: Iterable[tuple[str, Any]]  # provided by BootstrapTableMeta
    table_args: TableArgs

    class Meta:
        table_args = {'data-toggle': "table", "data-icons-prefix": "fa"}

    def __init__(self, *, data_url: str, table_args: TableArgs | None = None) -> None:
        self.data_url = enforce_url_params(data_url, dict(self._enforced_url_params))
        # un-freeze the classes table args so it can be modified on the instance
        self.table_args = dict(self._table_args)
        self.table_args.setdefault('data-url', self.data_url)
        if table_args:
            self.table_args.update(table_args)

    @property
    def _columns(self) -> list[Column]:
        return [getattr(self, a) for a in self.column_attrname_map.values()]

    @property
    def columns(self) -> t.Sequence[Column]:
        """Wrapper for subclasses to override."""
        return self._columns

    def __repr__(self) -> str:
        return "<{cls} cols={numcols} data_url={data_url!r}>".format(
            cls=type(self).__name__,
            numcols=len(self.columns),
            data_url=self.data_url,
        )

    def _init_table_args(self) -> None:
        """Set the defaults of :py:attr:`table_args`"""
        default_args = {
            'data-toggle': "table",
            'data-url': self.data_url,
        }
        for key, val in default_args.items():
            self.table_args.setdefault(key, val)

    @property
    @lazy_join
    def table_header(self) -> t.Iterator[HasDunderStr]:
        yield "<thead>"
        yield "<tr>"
        yield from self.columns
        yield "</tr>"
        yield "</thead>"

    @property
    def toolbar(self) -> HasDunderStr | None:
        return ""

    @property
    def table_footer(self) -> HasDunderStr | None:
        return ""

    @lazy_join("\n")
    def _render(self, table_id: str) -> t.Iterator[HasDunderStr | None]:
        toolbar_args = html_params(id=f"{table_id}-toolbar",
                                   class_="btn-toolbar",
                                   role="toolbar")
        yield f"<div {toolbar_args}>"
        yield self.toolbar
        yield "</div>"

        table_args = self.table_args
        table_args.update({
            'id': table_id,
            'data-toolbar': f"#{table_id}-toolbar",
        })

        yield f"<table {html_params(**table_args)}>"
        yield self.table_header
        yield self.table_footer
        yield "</table>"

    def render(self, table_id: str) -> Markup:
        """Render the table, use _render() directly if jinja2 isn't available
        """
        return Markup(self._render(table_id))


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
    splits: Iterable[tuple[str, str]]

    def _iter_typed_splits(self) -> t.Iterator[TableSplit]:
        for t in self.splits:  # noqa: F402
            yield TableSplit(*t)

    @property
    def columns(self) -> list[Column]:
        cols: list[Column] = []
        unaltered_columns = self._columns
        for split in self._iter_typed_splits():
            for c in unaltered_columns:
                prefixed_col = copy(c)
                prefixed_col.name = f"{split.prefix}_{c.name}"
                cols.append(prefixed_col)
        return cols

    @property  # type: ignore[arg-type]
    @lazy_join
    def table_header(self) -> t.Iterable[HasDunderStr]:
        yield "<thead>"
        yield "<tr>"
        for split in self._iter_typed_splits():
            yield (
                f'<th colspan="{len(super().columns)}" class="text-center">{split.title}</th>')
        yield "</tr>"

        yield "<tr>"
        yield from self.columns
        yield "</tr>"
        yield "</thead>"


def iso_format(dt: datetime | date | None = None) -> str:
    if dt is None:
        return "n/a"

    if isinstance(dt, date):
        return dt.isoformat()

    return dt.isoformat(sep=' ')


def date_format(
    dt: datetime | date | None,
    default: str | None = None,
    formatter: Callable = iso_format,
) -> DateColResponse:
    if not dt:
        return DateColResponse(
            formatted=default if default is not None else formatter(None),
            timestamp=None,
        )
    return DateColResponse(
        formatted=formatter(dt),
        timestamp=int(
            datetime.combine(dt, time.min.replace(tzinfo=timezone.utc)).timestamp()
        ),
    )


def datetime_format(
    dt: datetime | None,
    default: str | None = None,
    formatter: Callable = iso_format,
) -> DateColResponse:
    if dt is None:
        return DateColResponse(
            formatted=default if default is not None else formatter(None),
            timestamp=None,
        )
    return DateColResponse(
        formatted=formatter(dt),
        timestamp=int(dt.timestamp()),
    )


def enforce_url_params(url: str, params: dict[str, str]) -> str:
    """Safely enforce query values in an url

    :param url: The url to patch
    :param params: The parameters to enforce in the URL query part
    """
    if not params:
        return url
    # we need to use a list because of mutability
    url_parts = list(urlparse(url))
    query_parts = dict(parse_qsl(url_parts[4]))
    query_parts.update(params)
    url_parts[4] = urlencode(query_parts)
    return urlunparse(url_parts)


@lazy_join
def button_toolbar(
    title: str, href: str, id: str | bool = False, icon: str = "fa-plus"
) -> t.Iterator[str]:
    params = html_params(
        class_="btn btn-default btn-outline-secondary", href=href, id=id
    )
    yield f"<a {params}>"
    yield f"<span class=\"fa {icon}\"></span>"
    yield " "
    yield title
    yield "</a>"


@lazy_join
def toggle_button_toolbar(
    title: str, id: str, icon: str = "fa-plus"
) -> t.Iterator[str]:
    yield f'<input type="checkbox" class="btn-check" autocomplete="off" id="{id}">'
    yield f'<label class="btn btn-default btn-outline-secondary" for="{id}">'
    yield f"<span class=\"fa {icon}\"></span>"
    yield " "
    yield title
    yield "</label>"


HtmlParamValue = HasDunderStr | bool | None


def html_params(**kwargs: HtmlParamValue) -> str:
    """
    Generate HTML attribute syntax from inputted keyword arguments.
    """

    params = []
    for k, v in sorted(kwargs.items()):
        k = k.rstrip("_")

        if v is True:
            v = 'true'
        elif v is False:
            continue

        params.append(f'{str(k)}="{html.escape(str(v))}"')

    return ' '.join(params)


TRow = t.TypeVar("TRow", bound=BaseModel)


class TableResponse(BaseModel, t.Generic[TRow]):
    items: list[TRow]
