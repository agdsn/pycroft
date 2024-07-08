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
from functools import partial, cached_property

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

    def __init__(
        self,
        element: Constraint,
        if_exists: bool = False,
        cascade: bool = False,
        **kw: t.Any,
    ):
        super().__init__(element, cascade, **kw)
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


class Function(schema.DDLElement):

    def __init__(
        self,
        name: str,
        arguments: t.Iterable[str],
        rtype: str,
        definition: str | Selectable,
        volatility: t.Literal["volatile", "stable", "immutable"] = "volatile",
        strict: bool = False,
        leakproof: bool = False,
        language: str = "sql",
        quote_tag: str = "",
    ):
        """
        Represents PostgreSQL function

        :param name: Name of the function (excluding arguments).
        :param arguments: Arguments of the function.  A function
            identifier of ``new_function(integer, integer)`` would
            result in ``arguments=['integer', 'integer']``.
        :param rtype: Return type
        :param definition: Definition
        :param volatility: Either 'volatile', 'stable', or
            'immutable'
        :param strict: Function should be declared STRICT
        :param leakproof: Function should be declared LEAKPROOF
        :param str language: Language the function is defined in
        :param str quote_tag: Dollar quote tag to enclose the function
            definition
        """
        if volatility not in ('volatile', 'stable', 'immutable'):
            raise ValueError("volatility must be 'volatile', 'stable', or "
                             "'immutable'")
        self.name = name
        self.arguments = arguments
        self._definition = definition
        self.volatility = volatility
        self.strict = strict
        self.rtype = rtype
        self.language = language
        self.leakproof = leakproof
        self.quote_tag = quote_tag

    @cached_property
    def definition(self) -> str:
        if isinstance(self._definition, str):
            return inspect.cleandoc(self._definition)

        if isinstance(self._definition, Selectable):
            return str(
                self._definition.compile(
                    dialect=t.cast(type[Dialect], postgresql.dialect)(),
                    compile_kwargs={"literal_binds": True},
                )
            )

        raise ValueError(f"definition must be str or Selectable, not {type(self._definition)}")

    def build_quoted_identifier(self, quoter: t.Callable[[str], str]) -> str:
        """Compile the function identifier from name and arguments.

        :param quoter: A callable that quotes the function name

        :returns: The compiled string, like
                  ``"my_function_name"(integer, account_type)``
        """
        return "{name}({args})".format(
            name=quoter(self.name),
            args=", ".join(self.arguments),
        )


class CreateFunction(schema.DDLElement):
    """
    Represents a CREATE FUNCTION DDL statement
    """

    def __init__(self, func: Function, or_replace: bool = False):
        self.function = func
        self.or_replace = or_replace


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


class Rule(schema.DDLElement):
    def __init__(
        self,
        name: str,
        table: Table,
        event: str,
        command_or_commands: str | t.Sequence[str],
        condition: str | None = None,
        do_instead: bool = False,
    ) -> None:
        self.name = name
        self.table = table
        self.event = event
        self.condition = condition
        self.do_instead = do_instead
        self.commands: tuple[str, ...]
        if isinstance(command_or_commands, Iterable) and not isinstance(command_or_commands, str):
            self.commands = tuple(command_or_commands)
        else:
            self.commands = (command_or_commands,)


class CreateRule(schema.DDLElement):
    """
    Represents a CREATE RULE DDL statement
    """

    def __init__(self, rule: Rule, or_replace: bool = False) -> None:
        self.rule = rule
        self.or_replace = or_replace


class DropRule(schema.DDLElement):
    """
    Represents a DROP RULE DDL statement
    """

    def __init__(self, rule: Rule, if_exists: bool = False, cascade: bool = False) -> None:
        """
        :param rule:
        :param if_exists:
        :param cascade:
        """
        self.rule = rule
        self.if_exists = if_exists
        self.cascade = cascade


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


# TODO add type hints
class Trigger(schema.DDLElement):
    def __init__(
        self,
        name: str,
        table: Table,
        events: t.Sequence[str],
        function_call: str,
        when: t.Literal["BEFORE", "AFTER", "INSTEAD OF"] = "AFTER",
    ) -> None:
        """Construct a trigger

        :param name: Name of the trigger
        :param table: Table the trigger is for
        :param events: list of events (INSERT, UPDATE, DELETE)
        :param function_call: call of the trigger function
        :param when: Mode of execution
        """
        self.name = name
        self.table = table
        self.events = events
        self.function_call = function_call
        if when not in {"BEFORE", "AFTER", "INSTEAD OF"}:
            raise ValueError("`when` must be one of BEFORE, AFTER, INSTEAD OF")
        self.when = when


class ConstraintTrigger(Trigger):
    def __init__(
        self,
        *args: t.Any,
        deferrable: bool = False,
        initially_deferred: bool = False,
        **kwargs: t.Any,
    ) -> None:
        """Construct a Constraint Trigger

        :param deferrable: Constraint can be deferred
        :param initially_deferred: Constraint is set to deferred
        """
        super().__init__(*args, **kwargs)
        self.deferrable = deferrable
        if not deferrable and initially_deferred:
            raise ValueError("Constraint declared INITIALLY DEFERRED must be "
                             "DEFERRABLE.")
        self.initially_deferred = initially_deferred


class CreateTrigger(schema.DDLElement):
    def __init__(self, trigger: Trigger) -> None:
        self.trigger = trigger


class CreateConstraintTrigger(schema.DDLElement):
    """
    Represents a CREATE CONSTRAINT TRIGGER DDL statement
    """

    def __init__(self, constraint_trigger: ConstraintTrigger) -> None:
        self.constraint_trigger = constraint_trigger


class DropTrigger(schema.DDLElement):
    """
    Represents a DROP TRIGGER DDL statement.
    """

    def __init__(self, trigger: Trigger, if_exists: bool = False, cascade: bool = False) -> None:
        self.trigger = trigger
        self.if_exists = if_exists
        self.cascade = cascade


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


class View(schema.DDLElement):
    def __init__(
        self,
        name: str,
        query: SelectBase,
        column_names: t.Sequence[str] = None,
        temporary: bool = False,
        view_options: t.Mapping[str, t.Any] = None,
        check_option: t.Literal["local", "cascaded"] | None = None,
        materialized: bool = False,
    ) -> None:
        """DDL Element representing a VIEW

        :param name: The name of the view
        :param query: the query it represents
        :param column_names:
        :param temporary:
        :param view_options: Must be something that can be passed to
            OrderedDict, so a simple dict suffices.
        :param check_option: Must be one of ``None``, ``'local'``,
            ``'cascaded'``.
        :param materialized: Is materialized view
        """
        self.name = name
        self.query = query
        self.table = table(name)
        self.temporary = temporary
        self.column_names = column_names
        self._init_table_columns()
        if view_options is None:
            view_options = OrderedDict()
        else:
            view_options = OrderedDict(view_options)
        self.view_options = view_options
        if check_option not in (None, 'local', 'cascaded'):
            raise ValueError("check_option must be either None, 'local', or "
                             "'cascaded'")
        if check_option is not None and 'check_option' in view_options:
            raise ValueError('Parameter "check_option" specified more than '
                             'once')
        self.check_option = check_option
        self.materialized = materialized

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


class CreateView(schema.DDLElement):
    def __init__(self, view: View, or_replace: bool = False, if_not_exists: bool = False) -> None:
        self.view = view
        self.or_replace = or_replace
        self.if_not_exists = if_not_exists


class DropView(schema.DDLElement):
    def __init__(self, view: View, if_exists: bool = False, cascade: bool = False) -> None:
        self.view = view
        self.if_exists = if_exists
        self.cascade = cascade


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
