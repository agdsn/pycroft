#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
"""
ldap_sync.config
~~~~~~~~~~~~~~~~
"""
from __future__ import annotations

import os
from typing import NamedTuple
from distutils.util import strtobool

from . import logger, types


class SyncConfig(NamedTuple):
    # DB-related
    db_uri: str
    # LDAP-related
    host: str
    port: int
    use_ssl: bool
    ca_certs_file: str | None
    ca_certs_data: str | None
    bind_dn: types.DN
    bind_pw: str
    base_dn: types.DN
    required_property: str


def _from_environ_or_defaults(key: str, defaults: dict[str, str | None]) -> str | None:
    try:
        return os.environ[f'PYCROFT_LDAP_{key.upper()}']
    except KeyError as e:
        if key not in defaults:
            print("defaults:", defaults)
            raise ValueError(f"Missing configuration key {key}") from e
        return defaults[key]


def get_config(**defaults: str | None) -> SyncConfig:
    """Fetch the config from the environments, filling in defaults as specified.

    Values are converted in accordance to the types hints of :class:`SyncConfig`.

    The environment variables need to be of the format is ``PYCROFT_LDAP_$VAR``, e.g.
    ``PYCROFT_LDAP_PORT``.
    """
    db_uri = os.environ["PYCROFT_DB_URI"]
    config_dict: dict[str, str | None] = {
        # e.g. 'host': 'PYCROFT_LDAP_HOST'
        key: _from_environ_or_defaults(key, defaults)
        for key in SyncConfig._fields if key != 'db_uri'
    }

    def _get_or_fail(dict: dict[str, str | None], key: str) -> str:
        if (str_value := dict.pop(key)) is None:
            raise ValueError(f"{key} not found in environ or defaults")
        return str_value

    port = int(_get_or_fail(config_dict, "port"))
    use_ssl = bool(strtobool(_get_or_fail(config_dict, "use_ssl")))
    bind_dn = types.DN(_get_or_fail(config_dict, "bind_dn"))
    base_dn = types.DN(_get_or_fail(config_dict, "base_dn"))

    return SyncConfig(
        db_uri=db_uri,
        port=port,
        use_ssl=use_ssl,
        bind_dn=bind_dn,
        base_dn=base_dn,
        **config_dict,
    )


def get_config_or_exit(**defaults: str | None) -> SyncConfig:
    """See :func:`get_config`"""
    try:
        return get_config(**defaults)
    except KeyError as exc:
        logger.critical("%s not set, quitting", exc.args[0])
        exit()
