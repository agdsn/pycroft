# Copyright (c) 2015-2017 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
pycroft.model.ddl
~~~~~~~~~~~~~~~~~
"""
import inspect
import typing as t
from collections import OrderedDict
from collections.abc import Iterable
from dataclasses import dataclass, field
from functools import partial

from sqlalchemy import event as sqla_event, schema, table, text, Constraint, Table
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Dialect
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql import ClauseElement, Selectable, ColumnCollection
from sqlalchemy.sql.compiler import Compiled
from sqlalchemy.sql.selectable import SelectBase

from pycroft.model.session import with_transaction, session


def _join_tokens(*tokens: str | None) -> str:
    """
    Join all elements that are not None
    :param tokens:
    :return:
    """
    return ' '.join(token for token in tokens if token is not None)


def compile_if_clause(compiler: Compiled, clause: t.Any) -> t.Any:
    if isinstance(clause, ClauseElement):
        return str(clause.compile(compile_kwargs={"literal_binds": True}, dialect=compiler.dialect))
        return compiler.sql_compiler.process(clause, literal_binds=True)
    return clause


class DropConstraint(schema.DropConstraint):
    """
    Extends SQLALchemy's DropConstraint with support for IF EXISTS
    """

    @t.override
    def __init__(
        self,
        element: Constraint,
        if_exists: bool = False,
        cascade: bool = False,
        **kw: t.Any,
    ):
        super().__init__(element, cascade=cascade, **kw)
        self.element = element
        self.if_exists = if_exists
        self.cascade = cascade


# noinspection PyUnusedLocal
@compiles(DropConstraint, "postgresql")
def visit_drop_constraint(drop_constraint: DropConstraint, compiler: Compiled, **kw):
    constraint = drop_constraint.element
    opt_if_exists = "IF EXISTS" if drop_constraint.if_exists else None
    opt_drop_behavior = "CASCADE" if drop_constraint.cascade else None
    table_name = compiler.preparer.format_table(constraint.table)
    constraint_name = compiler.preparer.quote(constraint.name)
    return _join_tokens(
        "ALTER TABLE", table_name, "DROP CONSTRAINT", opt_if_exists,
        constraint_name, opt_drop_behavior)


def _process(value: str | Selectable) -> str:
    if isinstance(value, str):
        return inspect.cleandoc(value)

    if isinstance(value, Selectable):
        return str(
            value.compile(
                dialect=t.cast(type[Dialect], postgresql.dialect)(),
                compile_kwargs={"literal_binds": True},
            )
        )
        raise ValueError(f"Definition must be str or Selectable, not {type(value)}")


class LazilyComiledDefDescriptor:
    def __set_name__(self, owner, name):
        self._name = f"_{name}"

    def __get__(self, obj, type) -> str:
        # TODO cache this thing
        if obj is None:
            # this is interpreted as the default by the `dataclass` decorator
            return None
        value_unprocessed = getattr(obj, self._name)
        return _process(value_unprocessed)

    def __set__(self, obj, value: str | Selectable):
        setattr(obj, self._name, value)


@dataclass
class Function(schema.DDLElement):
    #: Name of the function (excluding arguments).
    name: str
    #: Arguments of the function.  A function
    #:   identifier of ``new_function(integer, integer)`` would
    #:   result in ``arguments=['integer', 'integer']``.
    arguments: t.Iterable[str]
    #: Return type
    rtype: str
    #: Definition
    definition: LazilyComiledDefDescriptor = field(default=LazilyComiledDefDescriptor(), repr=False)
    volatility: t.Literal["volatile", "stable", "immutable"] = "volatile"
    #: Function should be declared ``STRICT``
    strict: bool = False
    #: Function should be declared ``LEAKPROOF``
    leakproof: bool = False
    #: Language the function is defined in (e.g. ``plpgsql`` for trigger functions)
    language: str = "sql"
    #: Dollar quote tag to enclose the function definition
    quote_tag: str = ""

    def build_quoted_identifier(self, quoter: t.Callable[[str], str]) -> str:
        """Compile the function identifier from name and arguments.

        :param quoter: A callable that quotes the function name

        :returns: The compiled string, like
                  ``"my_function_name"(integer, account_type)``
        """
        name = quoter(self.name)
        args = ", ".join(self.arguments)
        return f"{name}({args})"

    def __hash__(self):
        return hash(self.name)


@dataclass(unsafe_hash=True)
class CreateFunction(schema.DDLElement):
    """
    Represents a CREATE FUNCTION DDL statement
    """

    func: Function

    @property
    def function(self) -> Function:
        return self.func

    or_replace: bool = False


class DropFunction(schema.DDLElement):
    """
    Represents a DROP FUNCTION DDL statement
    """

    def __init__(self, func: Function, if_exists: bool = False, cascade: bool = False):
        self.function = func
        self.if_exists = if_exists
        self.cascade = cascade


# noinspection PyUnusedLocal
@compiles(CreateFunction, "postgresql")
def visit_create_function(element: CreateFunction, compiler: Compiled, **kw: t.Any) -> str:
    """
    Compile a CREATE FUNCTION DDL statement for PostgreSQL
    """
    func = element.function
    opt_or_replace = 'OR REPLACE' if element.or_replace else None
    volatility = func.volatility.upper()
    strictness = "STRICT" if func.strict else None
    leakproof = "LEAKPROOF" if func.leakproof else None
    quoted_definition = "${quote_tag}$\n{definition}\n${quote_tag}$".format(
        quote_tag=func.quote_tag, definition=func.definition)

    function_name = func.build_quoted_identifier(quoter=compiler.preparer.quote)
    return _join_tokens(
        "CREATE", opt_or_replace, "FUNCTION", function_name, "RETURNS",
        func.rtype, volatility, strictness, leakproof, "LANGUAGE", func.language,
        "AS", quoted_definition,
    )


# noinspection PyUnusedLocal
@compiles(DropFunction, "postgresql")
def visit_drop_function(element: DropFunction, compiler: Compiled, **kw: t.Any) -> str:
    """
    Compile a DROP FUNCTION DDL statement for PostgreSQL
    """
    opt_if_exists = "IF EXISTS" if element.if_exists else None
    opt_drop_behavior = "CASCADE" if element.cascade else None
    function_name = element.function.build_quoted_identifier(quoter=compiler.preparer.quote)
    return _join_tokens("DROP FUNCTION", opt_if_exists,
                        function_name, opt_drop_behavior)


@dataclass
class Rule(schema.DDLElement):
    name: str
    table: Table
    event: str
    command_or_commands: str | t.Sequence[str]
    commands: tuple[str, ...] = field(init=False)
    condition: str | None = None
    do_instead: bool = False

    def __post_init__(self):
        cs = self.command_or_commands
        if isinstance(cs, Iterable) and not isinstance(cs, str):
            self.commands = tuple(cs)
        else:
            self.commands = (cs,)


@dataclass(unsafe_hash=True)
class CreateRule(schema.DDLElement):
    """
    Represents a CREATE RULE DDL statement
    """

    rule: Rule
    or_replace: bool = False


@dataclass
class DropRule(schema.DDLElement):
    """
    Represents a DROP RULE DDL statement
    """

    rule: Rule
    if_exists: bool = False
    cascade: bool = False


# noinspection PyUnusedLocal
@compiles(CreateRule, "postgresql")
def visit_create_rule(element: CreateRule, compiler: Compiled, **kw: t.Any) -> str:
    """
    Compile a CREATE RULE DDL statement for PostgreSQL.
    """
    rule = element.rule
    opt_or_replace = "OR REPLACE" if element.or_replace else None
    where_clause = ("WHERE " + rule.condition if rule.condition is not None
                    else None)
    opt_instead = "INSTEAD" if rule.do_instead else None
    compiled_commands = tuple(map(partial(compile_if_clause, compiler),
                                  rule.commands))
    if len(compiled_commands) == 1:
        commands = compiled_commands[0]
    else:
        commands = "({})".format("; ".join(compiled_commands))
    rule_name = compiler.preparer.quote(rule.name)
    table_name = compiler.preparer.format_table(rule.table)
    return _join_tokens(
        "CREATE", opt_or_replace, "RULE", rule_name, "AS ON", rule.event, "TO",
        table_name, where_clause, "DO", opt_instead, commands)


# noinspection PyUnusedLocal
@compiles(DropRule, "postgresql")
def visit_drop_rule(element: DropRule, compiler: Compiled, **kw: t.Any) -> str:
    """
    Compile a DROP RULE DDL statement for PostgreSQL
    """
    rule = element.rule
    opt_if_exists = "IF EXISTS" if element.if_exists else None
    opt_drop_behavior = "CASCADE" if element.cascade else None
    rule_name = compiler.preparer.quote(rule.name)
    table_name = compiler.preparer.format_table(rule.table)
    return _join_tokens(
        "DROP RULE", opt_if_exists, rule_name, "ON", table_name,
        opt_drop_behavior)


@dataclass
class Trigger(schema.DDLElement):
    #: Name of the trigger
    name: str
    #: Table the trigger is for
    table: Table
    #: list of events (INSERT, UPDATE, DELETE)
    events: t.Sequence[str]
    #: call of the trigger function
    function_call: str
    #: Mode of execution
    when: t.Literal["BEFORE", "AFTER", "INSTEAD OF"] = "AFTER"

    def __hash__(self):
        return hash(self.name)


@dataclass
class ConstraintTrigger(Trigger):
    #: Constraint can be deferred
    deferrable: bool = False
    #: Constrait is ste to deferred
    initially_deferred: bool = False

    def __post_init__(self):
        if not self.deferrable and self.initially_deferred:
            raise ValueError("Constraint declared INITIALLY DEFERRED must be "
                             "DEFERRABLE.")

    @t.override
    def __hash__(self):
        return super().__hash__()


@dataclass(unsafe_hash=True)
class CreateTrigger(schema.DDLElement):
    trigger: Trigger


@dataclass(unsafe_hash=True)
class CreateConstraintTrigger(schema.DDLElement):
    """
    Represents a CREATE CONSTRAINT TRIGGER DDL statement
    """

    constraint_trigger: ConstraintTrigger


@dataclass(unsafe_hash=True)
class DropTrigger(schema.DDLElement):
    """
    Represents a DROP TRIGGER DDL statement.
    """

    trigger: Trigger
    if_exists: bool = False
    cascade: bool = False


# noinspection PyUnusedLocal
@compiles(CreateConstraintTrigger, "postgresql")
def create_add_constraint_trigger(
    element: CreateConstraintTrigger, compiler: Compiled, **kw: t.Any
) -> str:
    """
    Compile a CREATE CONSTRAINT TRIGGER DDL statement for PostgreSQL
    """
    trigger = element.constraint_trigger
    events = ' OR '.join(trigger.events)
    opt_deferrable = 'DEFERRABLE' if trigger.deferrable else None
    opt_initially_deferred = ('INITIALLY DEFERRED' if trigger.initially_deferred
                              else None)
    trigger_name = compiler.preparer.quote(trigger.name)
    table_name = compiler.preparer.format_table(trigger.table)
    return _join_tokens(
        "CREATE CONSTRAINT TRIGGER", trigger_name, trigger.when, events, 'ON',
        table_name, opt_deferrable, opt_initially_deferred,
        "FOR EACH ROW EXECUTE PROCEDURE", trigger.function_call)


# noinspection PyUnusedLocal
@compiles(CreateTrigger, "postgresql")
def create_add_trigger(element: CreateTrigger, compiler: Compiled, **kw: t.Any) -> str:
    """
    Compile a CREATE CONSTRAINT TRIGGER DDL statement for PostgreSQL
    """
    trigger = element.trigger
    events = ' OR '.join(trigger.events)
    trigger_name = compiler.preparer.quote(trigger.name)
    table_name = compiler.preparer.format_table(trigger.table)
    return _join_tokens(
        "CREATE TRIGGER", trigger_name, trigger.when, events, 'ON', table_name,
        "FOR EACH ROW EXECUTE PROCEDURE", trigger.function_call)


# noinspection PyUnusedLocal
@compiles(DropTrigger, "postgresql")
def visit_drop_trigger(element: DropTrigger, compiler: Compiled, **kw: t.Any) -> str:
    """
    Compile a DROP TRIGGER DDL statement for PostgreSQL
    """
    trigger = element.trigger
    opt_if_exists = "IF EXISTS" if element.if_exists else None
    opt_drop_behavior = "CASCADE" if element.cascade else None
    trigger_name = compiler.preparer.quote(trigger.name)
    table_name = compiler.preparer.format_table(trigger.table)
    return _join_tokens(
        "DROP TRIGGER", opt_if_exists, trigger_name, "ON", table_name,
        opt_drop_behavior)


@dataclass
class View(schema.DDLElement):
    #: The name of the view
    name: str
    #: the query it represents
    query: SelectBase
    column_names: t.Sequence[str] = None
    temporary: bool = False
    #: Must be something that can be passed to OrderedDict, so a simple dict suffices.
    view_options: t.Mapping[str, t.Any] = None
    #: Must be one of ``None``, ``'local'``, ``'cascaded'``.
    check_option: t.Literal["local", "cascaded"] | None = None
    #: Is materialized view
    materialized: bool = False

    table: Table = field(init=False)

    def __post_init__(self) -> None:
        self.table = table(self.name)
        self._init_table_columns()
        if self.view_options is None:
            self.view_options = OrderedDict()
        else:
            self.view_options = OrderedDict(self.view_options)

        if self.check_option not in (None, "local", "cascaded"):
            raise ValueError("check_option must be either None, 'local', or "
                             "'cascaded'")
        if self.check_option is not None and "check_option" in self.view_options:
            raise ValueError('Parameter "check_option" specified more than '
                             'once')

    def _init_table_columns(self):
        if self.column_names is not None:
            query_column_names = set(self.query.c.keys())
            my_column_names = set(self.column_names)
            if my_column_names != query_column_names:
                raise ValueError(
                    "The given column_names must coincide with the implicit columns of the query:"
                    f" {my_column_names!r} != {query_column_names!r}"
                )
        for c in t.cast(ColumnCollection, self.query.selected_columns):
            # _make_proxy doesn't attach the column to the selectable (`self.table`) anymore
            # since sqla commit:aceefb508ccd0911f52ff0e50324b3fefeaa3f16 (before 1.4.0)
            key, col = c._make_proxy(self.table)
            self.table._columns.add(col, key=key)  # type: ignore

    @with_transaction
    def refresh(self, concurrently=False):
        """Refreshes the current materialized view"""

        if not self.materialized:
            raise ValueError("Cannot refresh a non-materialized view")

        _con = "CONCURRENTLY " if concurrently else ""
        session.execute(text("REFRESH MATERIALIZED VIEW " + _con + self.name))

    def __hash__(self):
        return hash(self.name)


@dataclass(unsafe_hash=True)
class CreateView(schema.DDLElement):
    view: View
    or_replace: bool = False
    if_not_exists: bool = False


@dataclass(unsafe_hash=True)
class DropView(schema.DDLElement):
    view: View
    if_exists: bool = False
    cascade: bool = False


# noinspection PyUnusedLocal
@compiles(CreateView, "postgresql")
def visit_create_view(element: CreateView, compiler: Compiled, **kw: t.Any) -> str:
    view = element.view
    opt_or_replace = "OR REPLACE" if element.or_replace and not view.materialized else None
    opt_temporary = "TEMPORARY" if view.temporary else None
    if view.column_names is not None:
        quoted_column_names = map(compiler.preparer.quote, view.column_names)
        opt_column_names = "({})".format(', '.join(quoted_column_names))
    else:
        opt_column_names = None
    view_name = compiler.preparer.quote(view.name)
    if view.view_options:
        opt_view_options = "WITH ({})".format(
            ', '.join(f"{name} = {value}"
                      for name, value in view.view_options.items()))
    else:
        opt_view_options = None
    compiled_query = compiler.sql_compiler.process(view.query,
                                                   literal_binds=True)
    if view.check_option is not None:
        opt_check_option = 'WITH {} CHECK OPTION'.format(
            view.check_option.upper())
    else:
        opt_check_option = None

    view_type = "VIEW" if not view.materialized else "MATERIALIZED VIEW"
    opt_if_not_exists = "IF NOT EXISTS" if element.if_not_exists and view.materialized else None

    return _join_tokens(
        "CREATE", opt_or_replace, opt_temporary, view_type, opt_if_not_exists, view_name,
        opt_column_names, opt_view_options, "AS", compiled_query,
        opt_check_option)


# noinspection PyUnusedLocal
@compiles(DropView, "postgresql")
def visit_drop_view(element: DropView, compiler: Compiled, **kw: t.Any) -> str:
    view = element.view
    opt_if_exists = "IF EXISTS" if element.if_exists else None
    opt_drop_behavior = "CASCADE" if element.cascade else None
    view_name = compiler.preparer.quote(view.name)
    view_type = "VIEW" if not view.materialized else "MATERIALIZED VIEW"

    return _join_tokens(
        "DROP", view_type, opt_if_exists, view_name, opt_drop_behavior
    )


class DDLManager:
    """
    Ensures that create DDL statements are registered with SQLAlchemy in the
    order they were added to the manager and registers the drop DDL statements
    in the reverse order.

    Example usage:

    >>> from sqlalchemy import MetaData, Table, Column as C, Integer as I, String as S
    >>> table = Table('table', MetaData(), C('id', I, primary_key=True), C('name', S))
    >>> manager = DDLManager()
    >>> view = View('my_view', "select concat(name, ' hat das Spiel verloren') from table")
    >>> manager.add_view(table, view)
    >>> # … do other stuff
    >>> manager.register()
    """

    def __init__(self):
        self.objects: list[tuple[object, schema.DDLElement, schema.DDLElement]] = []

    def add(
        self,
        target: Table,
        create_ddl: schema.DDLElement,
        drop_ddl: schema.DDLElement,
        dialect: str | None = None,
    ):
        if dialect:
            create_ddl = t.cast(schema.DDLElement, create_ddl.execute_if(dialect=dialect))
            drop_ddl = t.cast(schema.DDLElement, drop_ddl.execute_if(dialect=dialect))
        self.objects.append((target, create_ddl, drop_ddl))

    def add_constraint(
        self, table: Table, constraint: Constraint, dialect: str | None = None
    ) -> None:
        self.add(
            table,
            schema.AddConstraint(constraint),
            DropConstraint(constraint, if_exists=True),
            dialect=dialect,
        )

    def add_function(self, table: Table, func: Function, dialect: str | None = None) -> None:
        self.add(
            table,
            CreateFunction(func, or_replace=True),
            DropFunction(func, if_exists=True),
            dialect=dialect,
        )

    def add_rule(self, table: Table, rule: Rule, dialect: str | None = None) -> None:
        self.add(
            table,
            CreateRule(rule, or_replace=True),
            DropRule(rule, if_exists=True),
            dialect=dialect,
        )

    def add_trigger(self, table: Table, trigger: Trigger, dialect: str | None = None) -> None:
        self.add(
            table,
            CreateTrigger(trigger),
            DropTrigger(trigger, if_exists=True),
            dialect=dialect,
        )

    def add_constraint_trigger(
        self,
        table: Table,
        constraint_trigger: ConstraintTrigger,
        dialect: str | None = None,
    ) -> None:
        self.add(
            table,
            CreateConstraintTrigger(constraint_trigger),
            DropTrigger(constraint_trigger, if_exists=True),
            dialect=dialect,
        )

    def add_view(
        self,
        table: Table,
        view: View,
        dialect: str | None = None,
        or_replace: bool = True,
        if_not_exists: bool = True,
    ) -> None:
        self.add(
            table,
            CreateView(view, or_replace=or_replace, if_not_exists=if_not_exists),
            DropView(view, if_exists=True),
            dialect=dialect,
        )

    def register(self) -> None:
        for target, create_ddl, _drop_ddl in self.objects:
            sqla_event.listen(target, 'after_create', create_ddl)
        for target, _create_ddl, drop_ddl in reversed(self.objects):
            sqla_event.listen(target, 'before_drop', drop_ddl)
