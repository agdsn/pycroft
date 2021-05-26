import pytest
from sqlalchemy import select

from pycroft.model.ddl import View, CreateView, DropView
from . import create_table, literal_compile


@pytest.fixture(scope='session')
def table():
    return create_table("table")  # must be named `table` because we also test quoting


def test_plain_create_view(table):
    view = View("view", select(table.c.id))
    stmt = CreateView(view)
    assert literal_compile(stmt) == (
        'CREATE VIEW view AS SELECT "table".id \n'
        'FROM "table"'
    )

def test_create_or_replace_view(table):
    view = View("view", select(table.c.id))
    stmt = CreateView(view, or_replace=True)
    assert literal_compile(stmt) == (
        'CREATE OR REPLACE VIEW view AS SELECT "table".id \n'
        'FROM "table"'
    )

def test_create_temporary_view(table):
    view = View("view", select(table.c.id), temporary=True)
    stmt = CreateView(view)
    assert literal_compile(stmt) == (
        'CREATE TEMPORARY VIEW view AS SELECT "table".id \n'
        'FROM "table"'
    )

def test_create_view_with_view_options(table):
    view = View("view", select(table.c.id), view_options=[
        ('check_option', 'cascaded'),
        ('security_barrier', 't'),
    ])
    stmt = CreateView(view)
    assert literal_compile(stmt) == (
        'CREATE VIEW view '
        'WITH (check_option = cascaded, security_barrier = t) '
        'AS SELECT "table".id \n'
        'FROM "table"'
    )

def test_create_view_with_check_option(table):
    view = View("view", select(table.c.id), check_option='cascaded')
    stmt = CreateView(view)
    assert literal_compile(stmt) == (
        'CREATE VIEW view '
        'AS SELECT "table".id \n'
        'FROM "table" '
        'WITH CASCADED CHECK OPTION'
    )

def test_drop_view(table):
    view = View("view", select(table.c.id))
    stmt = DropView(view)
    assert literal_compile(stmt) == (
        'DROP VIEW view'
    )

def test_drop_view_if_exists(table):
    view = View("view", select(table.c.id))
    stmt = DropView(view, if_exists=True)
    assert literal_compile(stmt) == (
        'DROP VIEW IF EXISTS view'
    )

def test_drop_view_cascade(table):
    view = View("view", select(table.c.id))
    stmt = DropView(view, cascade=True)
    assert literal_compile(stmt) == (
        'DROP VIEW view CASCADE'
    )
