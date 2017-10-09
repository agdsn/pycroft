# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import inspect

from sqlalchemy import event as sqla_event, schema
from sqlalchemy.ext.compiler import compiles


def _join_tokens(*tokens) -> str:
    """
    Join all elements that are not None
    :param tokens:
    :return:
    """
    return ' '.join(token for token in tokens if token is not None)


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
    return _join_tokens(
        "ALTER TABLE", constraint.table.name, "DROP CONSTRAINT", opt_if_exists,
        constraint.name, opt_drop_behavior)


class Function(schema.DDLElement):
    on = 'postgresql'

    def __init__(self, name, rtype, definition, volatility='volatile',
                 strict=False, leakproof=False, language='sql', quote_tag=''):
        """
        Represents PostgreSQL function

        :param str name: Name of the function (including arguments)
        :param str rtype: Return type
        :param str definition: Definition
        :param str volatility: Either 'volatile', 'stable', or 'immutable'
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
        self.definition = inspect.cleandoc(definition)
        self.volatility = volatility
        self.strict = strict
        self.rtype = rtype
        self.language = language
        self.leakproof = leakproof
        self.quote_tag = quote_tag


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

    def __init__(self, func, if_exists=False):
        self.function = func
        self.if_exists = if_exists


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
    return _join_tokens(
        "CREATE", opt_or_replace, "FUNCTION", func.name, "RETURNS",
        func.rtype, volatility, strictness, leakproof,
        quoted_definition)


# noinspection PyUnusedLocal
@compiles(DropFunction, 'postgresql')
def visit_drop_function(element, compiler, **kw):
    """
    Compile a DROP FUNCTION DDL statement for PostgreSQL
    """
    opt_if_exists = "IF EXISTS" if element.if_exists else None
    opt_drop_behavior = "CASCADE" if element.cascade else None
    return _join_tokens("DROP FUNCTION", opt_if_exists,
                        element.function.name, opt_drop_behavior)


class ConstraintTrigger(schema.DDLElement):
    def __init__(self, name, table, events, function_call,
                 deferrable=False, initially_deferred=False):
        """
        Construct a constraint trigger
        :param str name: Name of the trigger
        :param table: Table the trigger is for
        :param iterable[str] events: list of events (INSERT, UPDATE, DELETE)
        :param str function_call: call of the trigger function
        :param deferrable: Constraint can be deferred
        :param initially_deferred: Constraint is set to deferred
        """
        self.name = name
        self.table = table
        self.events = events
        self.function_call = function_call
        self.deferrable = deferrable
        self.initially_deferred = initially_deferred


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

    def __init__(self, trigger, if_exists=False):
        self.trigger = trigger
        self.if_exists = if_exists


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
    return _join_tokens(
        "CREATE CONSTRAINT TRIGGER", trigger.name, 'AFTER', events, 'ON',
        trigger.table.name, opt_deferrable, opt_initially_deferred,
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
    return _join_tokens(
        "DROP TRIGGER", opt_if_exists, trigger.name, "ON", trigger.table.name,
        opt_drop_behavior)


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

    def add_constraint_trigger(self, table, constraint_trigger, dialect=None):
        self.add(table, CreateConstraintTrigger(constraint_trigger),
                 DropTrigger(constraint_trigger), dialect=dialect)

    def register(self):
        for target, create_ddl, drop_ddl in self.objects:
            sqla_event.listen(target, 'after_create', create_ddl)
        for target, create_ddl, drop_ddl in reversed(self.objects):
            sqla_event.listen(target, 'before_drop', drop_ddl)


# TODO: HERE is the location to add other views (radius, user for pmacct)
# shreyder said „INSTEAD OF would be useful“ (but didn't say for what)
