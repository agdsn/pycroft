# -*- coding: utf-8; -*-

from collections import namedtuple

import ldap3
from sqlalchemy import create_engine

from .conn import conn_opts
from .ldap_model import Nutzer, metadata


_combined_response = namedtuple('CombinedLdapResponse',
                                ['user_response', 'group_response'])

def fetch_ldap_information():
    try:
        opts = conn_opts['ldap']
    except KeyError:
        raise ValueError("Ldap connection configuration missing."
                         " See conn.py.example for an example.")

    server = ldap3.Server(host=opts['host'], port=opts['port'],
                          get_info=ldap3.SCHEMA, tls=None)
    connection = ldap3.Connection(server, opts['bind_dn'], opts['bind_pw'],
                                  version=3, auto_bind=True,
                                  authentication=opts.get('authentication'),
                                  sasl_mechanism=opts.get('sasl_mechanism'),
                                  sasl_credentials=opts.get('sasl_credentials'))
    success = connection.bind()
    if not success:
        raise ValueError("Bind not successful. Perhaps check your `conn.py`")
    connection.search(search_base=opts['base_dn'], search_scope=ldap3.SUBTREE,
                      search_filter="(objectClass=inetOrgPerson)",
                      attributes=ldap3.ALL_ATTRIBUTES)
    user_response = connection.response
    connection.search(search_base=opts['group_base_dn'], search_scope=ldap3.LEVEL,
                      search_filter="(objectClass=*)",
                      attributes=ldap3.ALL_ATTRIBUTES)
    group_response = connection.response

    return _combined_response(user_response, group_response)


def create_ldap_tables(engine):
    metadata.create_all(bind=engine)


def first_ldap_field(dn):
    return dn.split(',')[0].split('=')[1]


IGNORE_GROUPS = ['Alle']

def parse_groups(group_response):
    """Parse group result into a group_name→list of uids relation.

    :param group_response: The group part of the response from the
        ldap search

    :returns: a mapping {group_name: list of member uids}
    :rtype: dict
    """
    group_mappings = {}
    for group in group_response:
        attrs = group['attributes']
        group_cn = attrs['cn'][0]
        if group_cn in IGNORE_GROUPS:
            continue

        members = group_mappings[group_cn] = []
        for member in attrs['member']:
            member_uid = first_ldap_field(member)
            members.append(member_uid)

    return group_mappings


def cache_ldap(session):
    """Import ldap entries into the cache database."""
    response = fetch_ldap_information()

    group_mappings = parse_groups(response.group_response)
    no_pw_count = 0

    print("Caching ldap…")

    for user_entry in response.user_response:
        attrs = user_entry['attributes']
        if 'userPassword' not in attrs:
            no_pw_count += 1
            attrs['userPassword'] = [None]
        session.add(Nutzer.from_ldap_attributes(attrs,
                                                group_mappings=group_mappings))
    if no_pw_count:
        print("  {}/{} ldap entries without `userPassword`."
              " Are you sure you have sufficient privileges?"
              .format(no_pw_count, len(response.user_response)))

    session.commit()
    print("  Cached {} ldap users".format(len(response.user_response)))
