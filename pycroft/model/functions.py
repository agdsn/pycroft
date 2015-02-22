# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
Add support for various functions present in Postgres to the SQLite SQLAlchemy
dialect.
"""
from sqlalchemy.exc import CompileError
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql import expression
from sqlalchemy.sql.functions import max as sa_max
from sqlalchemy.sql.functions import min as sa_min
from sqlalchemy.types import DateTime, Numeric, Integer


class greatest(expression.FunctionElement):
    type = Numeric()
    name = 'greatest'


class least(expression.FunctionElement):
    type = Numeric()
    name = 'least'


class sign(expression.FunctionElement):
    type = Integer()
    name = 'sign'


class utcnow(expression.FunctionElement):
    type = DateTime


@compiles(utcnow, 'postgresql')
def pg_utcnow(element, compiler, **kw):
    return "TIMEZONE('utc', STATEMENT_TIMESTAMP())"


@compiles(utcnow, 'sqlite')
def sqlite_utcnow(element, compiler, **kw):
    return "STRFTIME('%Y-%m-%d %H:%M:%f000', 'now')"


@compiles(greatest)
@compiles(least)
@compiles(sign)
def compile_default_function(element, compiler, **kw):
    return compiler.visit_function(element)


@compiles(greatest, 'sqlite')
def compile_sqlite_greatest(element, compiler, **kw):
    return compiler.visit_function(sa_max(*list(element.clauses)))


@compiles(least, 'sqlite')
def compile_sqlite_least(element, compiler, **kw):
    return compiler.visit_function(sa_min(*list(element.clauses)))


@compiles(sign, 'sqlite')
def compile_sqlite_sign(element, compiler, **kw):
    args = list(element.clauses)
    if len(args) != 1:
        raise CompileError("Sign function takes exactly one argument.")
    return (
        "CASE WHEN {0} < 0 THEN -1 "
        "ELSE CASE WHEN {0} > 0 THEN 1 "
        "ELSE 0 END END".format(
            compiler.process(args[0])
        )
    )
