# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
pycroft.model.functions
~~~~~~~~~~~~~~~~~~~~~~~

Add support for various functions present in Postgres to the SQLite SQLAlchemy
dialect.
"""
from sqlalchemy.exc import CompileError
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql import expression
from sqlalchemy.sql.functions import max as sa_max
from sqlalchemy.sql.functions import min as sa_min
from sqlalchemy.types import Numeric, Integer


class greatest(expression.FunctionElement):
    inherit_cache = True
    type = Numeric()
    name = 'greatest'


class least(expression.FunctionElement):
    inherit_cache = True
    type = Numeric()
    name = 'least'


class sign(expression.FunctionElement):
    inherit_cache = True
    type = Integer()
    name = 'sign'


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
