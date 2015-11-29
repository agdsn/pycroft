# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import inspect

from sqlalchemy import event
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql import ddl
from sqlalchemy.sql.ddl import AddConstraint


class DropConstraint(ddl.DropConstraint):
    """
    Extends SQLALchemy's DropConstraint with support for IF EXISTS
    """
    def __init__(self, element, if_exists=False, cascade=False, **kw):
        super(DropConstraint, self).__init__(element, cascade, **kw)
        self.element = element
        self.if_exists = if_exists
        self.cascade = cascade


@compiles(DropConstraint, 'postgresql')
def visit_drop_constraint(drop_constraint, compiler, **kw):
    constraint = drop_constraint.element
    return (
        "ALTER TABLE {table} DROP CONSTRAINT {if_exists} {name} {cascade}"
    ).format(
        table=constraint.table.name, name=constraint.name,
        if_exists='IF EXISTS' if drop_constraint.if_exists else '',
        cascade='CASCADE' if drop_constraint.cascade else '',
    )


class Function(ddl.DDLElement):
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


class CreateFunction(ddl.DDLElement):
    """
    Represents a CREATE FUNCTION DDL statement
    """
    on = 'postgresql'

    def __init__(self, function):
        self.function = function


class DropFunction(ddl.DDLElement):
    """
    Represents a DROP FUNCTION DDL statement
    """
    on = 'postgresql'

    def __init__(self, function):
        self.function = function


@compiles(CreateFunction, 'postgresql')
def visit_create_function(element, compiler, **kw):
    """
    Compile a CREATE FUNCTION DDL statement for PostgreSQL
    """
    function = element.function
    return (
        "CREATE OR REPLACE FUNCTION {name} RETURNS {rtype} {volatility} "
        "{strict} {leakproof} LANGUAGE {language} AS "
        "${quote_tag}${definition}${quote_tag}$"
    ).format(
        name=function.name, rtype=function.rtype,
        volatility=function.volatility,
        strict='STRICT' if function.strict else 'CALLED ON NULL INPUT',
        language=function.language, definition=function.definition,
        leakproof='LEAKPROOF' if function.leakproof else '',
        quote_tag=function.quote_tag,
    )


@compiles(DropFunction, 'postgresql')
def visit_drop_function(element, compiler, **kw):
    """
    Compile a DROP FUNCTION DDL statement for PostgreSQL
    """
    return "DROP FUNCTION IF EXISTS {name}".format(name=element.function.name)


class ConstraintTrigger(ddl.DDLElement):
    def __init__(self, name, table, events, function_call):
        """
        Construct a constraint trigger
        :param str name: Name of the trigger
        :param table: Table the trigger is for
        :param iterable[str] events: list of events (INSERT, UPDATE, DELETE)
        :param str function_call: call of the trigger function
        """
        self.name = name
        self.table = table
        self.events = events
        self.function_call = function_call


class CreateConstraintTrigger(ddl.DDLElement):
    """
    Represents a CREATE CONSTRAINT TRIGGER DDL statement
    """
    on = 'postgresql'

    def __init__(self, constraint_trigger):
        self.constraint_trigger = constraint_trigger


class DropTrigger(ddl.DDLElement):
    """
    Represents a DROP TRIGGER DDL statement.
    """
    on = 'postgresql'

    def __init__(self, trigger):
        self.trigger = trigger


@compiles(CreateConstraintTrigger, 'postgresql')
def create_add_constraint_trigger(element, compiler, **kw):
    """
    Compile a CREATE CONSTRAINT TRIGGER DDL statement for PostgreSQL
    """
    trigger = element.constraint_trigger
    return "CREATE CONSTRAINT TRIGGER {name} AFTER {events} ON {table} " \
           "DEFERRABLE INITIALLY DEFERRED " \
           "FOR EACH ROW EXECUTE PROCEDURE {function}".format(
        name=trigger.name, events=' OR '.join(trigger.events),
        table=trigger.table.name, function=trigger.function_call)


@compiles(DropTrigger, 'postgresql')
def visit_drop_trigger(element, compiler, **kw):
    """
    Compile a DROP TRIGGER DDL statement for PostgreSQL
    """
    return "DROP TRIGGER IF EXISTS {name} ON {table}".format(
        name=element.trigger.name,
        table=element.trigger.table.name
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
        self.add(table, AddConstraint(constraint),
                 DropConstraint(constraint, if_exists=True), dialect=dialect)

    def add_function(self, table, function, dialect=None):
        self.add(table, CreateFunction(function), DropFunction(function),
                 dialect=dialect)

    def add_constraint_trigger(self, table, constraint_trigger, dialect=None):
        self.add(table, CreateConstraintTrigger(constraint_trigger),
                 DropTrigger(constraint_trigger), dialect=dialect)

    def register(self):
        for target, create_ddl, drop_ddl in self.objects:
            event.listen(target, 'after_create', create_ddl)
        for target, create_ddl, drop_ddl in reversed(self.objects):
            event.listen(target, 'before_drop', drop_ddl)
