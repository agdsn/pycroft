# Copyright (c) 2015-2017 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import inspect
from collections import OrderedDict
from collections.abc import Iterable
from functools import partial

from sqlalchemy import event as sqla_event, schema, table
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql import ClauseElement

from pycroft.model.session import with_transaction, session


def _join_tokens(*tokens):
    """
    Join all elements that are not None
    :param tokens:
    :return:
    """
    return ' '.join(token for token in tokens if token is not None)


def compile_if_clause(compiler, clause):
    if isinstance(clause, ClauseElement):
        return str(clause.compile(compile_kwargs={'literal_binds': True},
                                  dialect=compiler.dialect))
        return compiler.sql_compiler.process(clause, literal_binds=True)
    return clause


class DropConstraint(schema.DropConstraint):
    """
    Extends SQLALchemy's DropConstraint with support for IF EXISTS
    """
    def __init__(self, element, if_exists=False, cascade=False, **kw):
        super(DropConstraint, self).__init__(element, cascade, **kw)
        self.element = element
        self.if_exists = if_exists
        self.cascade = cascade


# noinspection PyUnusedLocal
@compiles(DropConstraint, 'postgresql')
def visit_drop_constraint(drop_constraint, compiler, **kw):
    constraint = drop_constraint.element
    opt_if_exists = 'IF EXISTS' if drop_constraint.if_exists else None
    opt_drop_behavior = 'CASCADE' if drop_constraint.cascade else None
    table_name = compiler.preparer.format_table(constraint.table)
    constraint_name = compiler.preparer.quote(constraint.name)
    return _join_tokens(
        "ALTER TABLE", table_name, "DROP CONSTRAINT", opt_if_exists,
        constraint_name, opt_drop_behavior)


class Function(schema.DDLElement):
    on = 'postgresql'

    def __init__(self, name, arguments, rtype, definition, volatility='volatile',
                 strict=False, leakproof=False, language='sql', quote_tag=''):
        """
        Represents PostgreSQL function

        :param str name: Name of the function (excluding arguments).
        :param list arguments: Arguments of the function.  A function
            identifier of ``new_function(integer, integer)`` would
            result in ``arguments=['integer', 'integer']``.
        :param str rtype: Return type
        :param str definition: Definition
        :param str volatility: Either 'volatile', 'stable', or
            'immutable'
        :param bool strict: Function should be declared STRICT
        :param bool leakproof: Function should be declared LEAKPROOF
        :param str language: Language the function is defined in
        :param str quote_tag: Dollar quote tag to enclose the function
            definition
        """
        if volatility not in ('volatile', 'stable', 'immutable'):
            raise ValueError("volatility must be 'volatile', 'stable', or "
                             "'immutable'")
        self.name = name
        self.arguments = arguments
        self.definition = inspect.cleandoc(definition)
        self.volatility = volatility
        self.strict = strict
        self.rtype = rtype
        self.language = language
        self.leakproof = leakproof
        self.quote_tag = quote_tag

    def build_quoted_identifier(self, quoter):
        """Compile the function identifier from name and arguments.

        :param quoter: A callable that quotes the function name

        :returns: The compiled string, like
                  ``"my_function_name"(integer, account_type)``
        :rtype: str
        """
        return "{name}({args})".format(
            name=quoter(self.name),
            args=", ".join(self.arguments),
        )



class CreateFunction(schema.DDLElement):
    """
    Represents a CREATE FUNCTION DDL statement
    """
    on = 'postgresql'

    def __init__(self, func, or_replace=False):
        self.function = func
        self.or_replace = or_replace


class DropFunction(schema.DDLElement):
    """
    Represents a DROP FUNCTION DDL statement
    """
    on = 'postgresql'

    def __init__(self, func, if_exists=False, cascade=False):
        self.function = func
        self.if_exists = if_exists
        self.cascade = cascade


# noinspection PyUnusedLocal
@compiles(CreateFunction, 'postgresql')
def visit_create_function(element, compiler, **kw):
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
@compiles(DropFunction, 'postgresql')
def visit_drop_function(element, compiler, **kw):
    """
    Compile a DROP FUNCTION DDL statement for PostgreSQL
    """
    opt_if_exists = "IF EXISTS" if element.if_exists else None
    opt_drop_behavior = "CASCADE" if element.cascade else None
    function_name = element.function.build_quoted_identifier(quoter=compiler.preparer.quote)
    return _join_tokens("DROP FUNCTION", opt_if_exists,
                        function_name, opt_drop_behavior)


class Rule(schema.DDLElement):
    on = 'postgresql'

    def __init__(self, name, table, event, command_or_commands,
                 condition=None, do_instead=False):
        self.name = name
        self.table = table
        self.event = event
        self.condition = condition
        self.do_instead = do_instead
        if (isinstance(command_or_commands, Iterable) and
                not isinstance(command_or_commands, str)):
            self.commands = tuple(command_or_commands)
        else:
            self.commands = (command_or_commands,)


class CreateRule(schema.DDLElement):
    """
    Represents a CREATE RULE DDL statement
    """
    on = 'postgresql'

    def __init__(self, rule, or_replace=False):
        self.rule = rule
        self.or_replace = or_replace


class DropRule(schema.DDLElement):
    """
    Represents a DROP RULE DDL statement
    """
    on = 'postgresql'

    def __init__(self, rule, if_exists=False, cascade=False):
        """
        :param rule:
        :param if_exists:
        :param cascade:
        """
        self.rule = rule
        self.if_exists = if_exists
        self.cascade = cascade


# noinspection PyUnusedLocal
@compiles(CreateRule, 'postgresql')
def visit_create_rule(element, compiler, **kw):
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
@compiles(DropRule, 'postgresql')
def visit_drop_rule(element, compiler, **kw):
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


class Trigger(schema.DDLElement):
    def __init__(self, name, table, events, function_call, when="AFTER"):
        """Construct a trigger

        :param str name: Name of the trigger
        :param table: Table the trigger is for
        :param iterable[str] events: list of events (INSERT, UPDATE, DELETE)
        :param str function_call: call of the trigger function
        :param str when: Mode of execution. Must be one of ``BEFORE``, ``AFTER``, ``INSTEAD OF``
        """
        self.name = name
        self.table = table
        self.events = events
        self.function_call = function_call
        if when not in {"BEFORE", "AFTER", "INSTEAD OF"}:
            raise ValueError("`when` must be one of BEFORE, AFTER, INSTEAD OF")
        self.when = when


class ConstraintTrigger(Trigger):
    def __init__(self, *args, deferrable=False, initially_deferred=False, **kwargs):
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
    on = 'postgresql'

    def __init__(self, trigger):
        self.trigger = trigger


class CreateConstraintTrigger(schema.DDLElement):
    """
    Represents a CREATE CONSTRAINT TRIGGER DDL statement
    """
    on = 'postgresql'

    def __init__(self, constraint_trigger):
        self.constraint_trigger = constraint_trigger


class DropTrigger(schema.DDLElement):
    """
    Represents a DROP TRIGGER DDL statement.
    """
    on = 'postgresql'

    def __init__(self, trigger, if_exists=False, cascade=False):
        self.trigger = trigger
        self.if_exists = if_exists
        self.cascade = cascade


# noinspection PyUnusedLocal
@compiles(CreateConstraintTrigger, 'postgresql')
def create_add_constraint_trigger(element, compiler, **kw):
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
@compiles(CreateTrigger, 'postgresql')
def create_add_trigger(element, compiler, **kw):
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
@compiles(DropTrigger, 'postgresql')
def visit_drop_trigger(element, compiler, **kw):
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
    def __init__(self, name, query,
                 column_names=None,
                 temporary=False,
                 view_options=None,
                 check_option=None,
                 materialized=False):
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
            if set(self.column_names) != query_column_names:
                raise ValueError("The given column_names must coincide with"
                                 " the implicit columns of the query: {!r} != {!r}"
                                 .format(set(self.column_names), query_column_names))
        for c in self.query.c:
            c._make_proxy(self.table)

    @with_transaction
    def refresh(self, concurrently=False):
        """Refreshes the current materialized view"""

        if not self.materialized:
            raise ValueError("Cannot refresh a non-materialized view")

        _con = 'CONCURRENTLY ' if concurrently else ''
        session.execute('REFRESH MATERIALIZED VIEW ' + _con + self.name)


class CreateView(schema.DDLElement):
    def __init__(self, view, or_replace=False):
        self.view = view
        self.or_replace = or_replace


class DropView(schema.DDLElement):
    def __init__(self, view, if_exists=False, cascade=False):
        self.view = view
        self.if_exists = if_exists
        self.cascade = cascade


# noinspection PyUnusedLocal
@compiles(CreateView, 'postgresql')
def visit_create_view(element, compiler, **kw):
    view = element.view
    opt_or_replace = "OR REPLACE" if element.or_replace else None
    opt_temporary = "TEMPORARY" if view.temporary else None
    if view.column_names is not None:
        quoted_column_names = map(compiler.preparer.quote, view.column_names)
        opt_column_names = "({})".format(', '.join(quoted_column_names))
    else:
        opt_column_names = None
    view_name = compiler.preparer.quote(view.name)
    if view.view_options:
        opt_view_options = "WITH ({})".format(
            ', '.join("{} = {}".format(name, value)
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

    return _join_tokens(
        "CREATE", opt_or_replace, opt_temporary, view_type, view_name,
        opt_column_names, opt_view_options, "AS", compiled_query,
        opt_check_option)


# noinspection PyUnusedLocal
@compiles(DropView, 'postgresql')
def visit_drop_view(element, compiler, **kw):
    view = element.view
    opt_if_exists = "IF EXISTS" if element.if_exists else None
    opt_drop_behavior = "CASCADE" if element.cascade else None
    view_name = compiler.preparer.quote(view.name)
    view_type = "VIEW" if not view.materialized else "MATERIALIZED VIEW"

    return _join_tokens(
        "DROP", view_type, opt_if_exists, view_name, opt_drop_behavior
    )


class DDLManager(object):
    """
    Ensures that create DDL statements are registered with SQLAlchemy in the
    order they were added to the manager and registers the drop DDL statements
    in the reverse order.
    """
    def __init__(self):
        self.objects = []

    def add(self, target, create_ddl, drop_ddl, dialect=None):
        if dialect:
            create_ddl = create_ddl.execute_if(dialect=dialect)
            drop_ddl = drop_ddl.execute_if(dialect=dialect)
        self.objects.append((target, create_ddl, drop_ddl))

    def add_constraint(self, table, constraint, dialect=None):
        self.add(table, schema.AddConstraint(constraint),
                 DropConstraint(constraint, if_exists=True), dialect=dialect)

    def add_function(self, table, func, dialect=None):
        self.add(table, CreateFunction(func, or_replace=True),
                 DropFunction(func, if_exists=True), dialect=dialect)

    def add_rule(self, table, rule, dialect=None):
        self.add(table, CreateRule(rule, or_replace=True),
                 DropRule(rule, if_exists=True), dialect=dialect)

    def add_trigger(self, table, trigger, dialect=None):
        self.add(table, CreateTrigger(trigger),
                 DropTrigger(trigger, if_exists=True), dialect=dialect)

    def add_constraint_trigger(self, table, constraint_trigger, dialect=None):
        self.add(table, CreateConstraintTrigger(constraint_trigger),
                 DropTrigger(constraint_trigger, if_exists=True), dialect=dialect)

    def add_view(self, table, view, dialect=None, or_replace=True):
        self.add(table, CreateView(view, or_replace=or_replace),
                 DropView(view, if_exists=True), dialect=dialect)

    def register(self):
        for target, create_ddl, drop_ddl in self.objects:
            sqla_event.listen(target, 'after_create', create_ddl)
        for target, create_ddl, drop_ddl in reversed(self.objects):
            sqla_event.listen(target, 'before_drop', drop_ddl)
