#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
import os
from typing import NamedTuple
from distutils.util import strtobool

from ldap_sync import logger


class SyncConfig(NamedTuple):
    # DB-related
    db_uri: str
    # LDAP-related
    host: str
    port: int
    use_ssl: bool
    ca_certs_file: str | None
    ca_certs_data: str | None
    bind_dn: str
    bind_pw: str
    base_dn: str
    required_property: str


def _from_environ_or_defaults(key: str, defaults: dict[str, str]) -> str:
    try:
        return os.environ[f'PYCROFT_LDAP_{key.upper()}']
    except KeyError as e:
        if key not in defaults:
            print("defaults:", defaults)
            raise ValueError(f"Missing configuration key {key}") from e
        return defaults[key]


def get_config(**defaults: str) -> SyncConfig:
    db_uri = os.environ["PYCROFT_DB_URI"]
    config_dict: dict[str, str] = {
        # e.g. 'host': 'PYCROFT_LDAP_HOST'
        key: _from_environ_or_defaults(key, defaults)
        for key in SyncConfig._fields if key != 'db_uri'
    }
    port = int(config_dict.pop("port"))
    use_ssl = bool(strtobool(config_dict.pop("use_ssl")))
    return SyncConfig(
        db_uri=db_uri,
        port=port,
        use_ssl=use_ssl,
        **config_dict,
    )


def get_config_or_exit(**defaults: str) -> SyncConfig:
    try:
        return get_config(**defaults)
    except KeyError as exc:
        logger.critical("%s not set, quitting", exc.args[0])
        exit()
