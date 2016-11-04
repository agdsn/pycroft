# -*- coding: utf-8; -*-
from __future__ import print_function

import ldap3
from sqlalchemy import create_engine

from conn import conn_opts


def get_ldap_results():
    try:
        opts = conn_opts['ldap']
    except KeyError:
        raise ValueError("Ldap connection configuration missing."
                         " See conn.py.example for an example.")

    server = ldap3.Server(host=opts['host'], port=opts['port'],
                          get_info=ldap3.SCHEMA, tls=None)
    connection = ldap3.Connection(server, opts['bind_dn'], opts['bind_pw'])
    connection.bind()
    connection.search(search_base=opts['base_dn'], search_scope=ldap3.SUBTREE,
                      search_filter="(objectClass=inetOrgPerson)",
                      attributes=ldap3.ALL_ATTRIBUTES)

    return connection.response


def import_ldap_entries(results):
    """Import ldap entries into the cache database.

    :param list results: The results from ldap3.Connection.search
    """
    # engine = create_engine(conn_opts['ldap'])
    # session = scoped_session(sessionmaker(bind=engine))
    for result in results:
        # form: attrs[…]
        print("Add user", result['dn'])
        # session.add(Nutzer.from_ldap_attributes(result['attributes']))
    # session.commit()


if __name__ == '__main__':
    ldap_results = get_ldap_results()

    print("Got {} results.".format(len(ldap_results)))

    import_ldap_entries(ldap_results)
