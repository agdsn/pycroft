import ldap3
import pytest

from ldap_sync.record import dn_from_username


@pytest.fixture(scope='class')
def connection():
    server = ldap3.Server('fake_server', get_info=ldap3.ALL)
    connection = ldap3.Connection(server, user='cn=test', password='pw',
                                  client_strategy=ldap3.MOCK_SYNC)
    connection.open()
    yield connection
    connection.strategy.close()


@pytest.fixture(scope='session')
def base():
    return 'ou=Nutzer,ou=Pycroft,dc=AG DSN,dc=de'


@pytest.fixture(scope='session')
def uid():
    return 'shizzle'


@pytest.fixture(scope='session')
def dn(uid, base):
    return dn_from_username(uid, base=base)
