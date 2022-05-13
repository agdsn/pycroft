#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
import os
from collections import namedtuple
from distutils.util import strtobool

from ldap_sync import logger

_sync_config = namedtuple(
    'LdapSyncConfig',
    ['host', 'port', 'use_ssl', 'ca_certs_file', 'ca_certs_data', 'bind_dn',
     'bind_pw', 'base_dn', 'db_uri', 'required_property']
)


def _from_environ_or_defaults(key, defaults):
    try:
        return os.environ[f'PYCROFT_LDAP_{key.upper()}']
    except KeyError as e:
        if key not in defaults:
            print("defaults:", defaults)
            raise ValueError(f"Missing configuration key {key}") from e
        return defaults[key]


def get_config(**defaults):
    config_dict = {
        # e.g. 'host': 'PYCROFT_LDAP_HOST'
        key: _from_environ_or_defaults(key, defaults)
        for key in _sync_config._fields if key != 'db_uri'
    }
    config_dict['port'] = int(config_dict['port'])
    if 'use_ssl' in config_dict:
        config_dict['use_ssl'] = bool(strtobool(config_dict['use_ssl']))
    config_dict['db_uri'] = os.environ['PYCROFT_DB_URI']
    config = _sync_config(**config_dict)

    return config


def get_config_or_exit(**defaults):
    try:
        return get_config(**defaults)
    except KeyError as exc:
        logger.critical("%s not set, quitting", exc.args[0])
        exit()
