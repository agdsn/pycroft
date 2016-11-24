# -*- coding: utf-8; -*-
from __future__ import print_function

import ldap3
from sqlalchemy import create_engine

from conn import conn_opts
from ldap_model import Nutzer


def get_ldap_results():
    try:
        opts = conn_opts['ldap']
    except KeyError:
        raise ValueError("Ldap connection configuration missing."
                         " See conn.py.example for an example.")

    server = ldap3.Server(host=opts['host'], port=opts['port'],
                          get_info=ldap3.SCHEMA, tls=None)
    connection = ldap3.Connection(server, opts['bind_dn'], opts['bind_pw'])
    success = connection.bind()
    if not success:
        raise ValueError("Bind not successful. Perhaps check your `conn.py`")
    connection.search(search_base=opts['base_dn'], search_scope=ldap3.SUBTREE,
                      search_filter="(objectClass=inetOrgPerson)",
                      attributes=ldap3.ALL_ATTRIBUTES)

    return connection.response


def create_ldap_tables(engine):
    Nutzer.metadata.create_all(bind=engine)


def cache_ldap(session, engine):
    """Import ldap entries into the cache database."""
    results = get_ldap_results()

    for result in results:
        session.add(Nutzer.from_ldap_attributes(result['attributes']))
    session.commit()
    print("Cached {} ldap entries".format(len(results)))
