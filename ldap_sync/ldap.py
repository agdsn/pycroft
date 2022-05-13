#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
import ssl

import ldap3

from ldap_sync import logger


def establish_and_return_ldap_connection(host, port, use_ssl, ca_certs_file,
                                         ca_certs_data, bind_dn, bind_pw):
    tls = None
    if ca_certs_file or ca_certs_data:
        tls = ldap3.Tls(ca_certs_file=ca_certs_file,
                        ca_certs_data=ca_certs_data, validate=ssl.CERT_REQUIRED)
    server = ldap3.Server(host=host, port=port, use_ssl=use_ssl, tls=tls)
    return ldap3.Connection(server, user=bind_dn, password=bind_pw, auto_bind=True)


def fetch_ldap_entries(connection, base_dn, search_filter=None, attributes=ldap3.ALL_ATTRIBUTES):
    success = connection.search(search_base=base_dn,
                                search_filter=search_filter,
                                attributes=attributes)
    if not success:
        logger.warning("LDAP search not successful.  Result: %s", connection.result)
        return []

    return [r for r in connection.response if r['dn'] != base_dn]


def fetch_current_ldap_users(connection, base_dn):
    return fetch_ldap_entries(connection, base_dn,
                              search_filter='(objectclass=inetOrgPerson)',
                              attributes=[ldap3.ALL_ATTRIBUTES, 'pwdAccountLockedTime'])


def fetch_current_ldap_groups(connection, base_dn):
    return fetch_ldap_entries(connection, base_dn, search_filter='(objectclass=groupOfMembers)')


def fetch_current_ldap_properties(connection, base_dn):
    return fetch_ldap_entries(connection, base_dn, search_filter='(objectclass=groupOfMembers)')


def fake_connection():
    server = ldap3.Server('mocked')
    connection = ldap3.Connection(server, client_strategy=ldap3.MOCK_SYNC)
    connection.open()
    return connection
