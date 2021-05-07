import pytest

from tests.model.ddl import create_table


@pytest.fixture(scope='session')
def table():
    return create_table('test')


@pytest.fixture(scope='session')
def table2():
    return create_table('test2')


@pytest.fixture(scope='session')
def table3():
    return create_table('test3')
