#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
import logging
import typing as t

import ldap3
import pytest

from ldap_sync.concepts import types
from ldap_sync.config import get_config, SyncConfig
from tests.ldap_sync import _cleanup_conn


@pytest.fixture(scope="class")
def muted_ldap_logger():
    logging.getLogger("ldap_sync").addHandler(logging.NullHandler())


class ConfigWithDNs(SyncConfig):
    @property
    def user_base_dn(self) -> types.DN:
        return types.DN(f"ou=users,{self.base_dn}")

    @property
    def group_base_dn(self) -> types.DN:
        return types.DN(f"ou=groups,{self.base_dn}")

    @property
    def property_base_dn(self) -> types.DN:
        return types.DN(f"ou=properties,{self.base_dn}")

    @property
    def policies_dn(self) -> types.DN:
        return types.DN(f"ou=policies,{self.base_dn}")

    def iter_bases_to_create(self):
        yield self.base_dn
        yield self.user_base_dn
        yield self.group_base_dn
        yield self.property_base_dn
        yield self.policies_dn


@pytest.fixture(scope="session")
def sync_config() -> ConfigWithDNs:
    return ConfigWithDNs(
        *get_config(
            required_property="mail",
            use_ssl="False",
            ca_certs_file=None,
            ca_certs_data=None,
        )
    )


@pytest.fixture(scope="session")
def ldap_server(sync_config) -> ldap3.Server:
    return ldap3.Server(host=sync_config.host, port=sync_config.port)


@pytest.fixture(scope="session")
def get_connection(ldap_server, sync_config) -> t.Callable[[], ldap3.Connection]:
    def get_connection():
        return ldap3.Connection(
            ldap_server,
            user=sync_config.bind_dn,
            password=sync_config.bind_pw,
            auto_bind="NO_TLS",
        )

    return get_connection


def _recursive_delete(conn: ldap3.Connection, base_dn: types.DN):
    conn.search(base_dn, "(objectclass=*)", ldap3.LEVEL)
    for response_item in conn.response:
        _recursive_delete(conn, response_item["dn"])
    conn.delete(base_dn)


@pytest.fixture
def clean_ldap_base(get_connection, sync_config):
    """Delete everything from an LDAP base, set up base dns and a default ppolicy."""
    with get_connection() as conn:
        _recursive_delete(conn, sync_config.base_dn)
        for base in sync_config.iter_bases_to_create():
            result = conn.add(base, "organizationalUnit")
            if not result:  # pragma: no cover
                raise RuntimeError(
                    f"Couldn't create dn {base} as organizationalUnit", result
                )

        result = conn.add(
            f"cn=default,{sync_config.policies_dn}",
            ["applicationProcess", "pwdPolicy"],
            {
                "pwdAllowUserChange": True,
                "pwdAttribute": "userPassword",
                "pwdCheckQuality": 1,
                "pwdExpireWarning": 604800,  # 7 days
                "pwdFailureCountInterval": 0,
                "pwdGraceAuthNLimit": 0,
                "pwdInHistory": 5,
                "pwdLockout": True,
                "pwdLockoutDuration": 1800,  # 30 minutes
                "pwdMaxAge": 15552000,  # 180 days
                "pwdMaxFailure": 5,
                "pwdMinAge": 0,
                "pwdMinLength": 6,
                "pwdMustChange": True,
            },
        )
        if not result:  # pragma: no cover
            raise RuntimeError(f"Could not create default password policy", result)
    _cleanup_conn(conn)


@pytest.fixture
def conn(get_connection) -> ldap3.Connection:
    with get_connection() as conn:
        yield conn
    _cleanup_conn(conn)
