"""
ldap_sync.__main__
~~~~~~~~~~~~~~~~~~
"""
import argparse
import logging
import os

from ldap3.utils.dn import safe_dn
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from ldap_sync.execution import execute_real
from ldap_sync.record_diff import bulk_diff_records
from .config import get_config_or_exit
from .exporter import sync_all
from .sources.ldap import (
    establish_and_return_ldap_connection,
    _fetch_ldap_users,
    _fetch_ldap_groups,
    _fetch_ldap_properties,
    fake_connection,
    fetch_ldap_users,
    fetch_ldap_groups,
    fetch_ldap_properties,
)
from ldap_sync import logger
from ldap_sync.concepts import types
from .sources.db import (
    establish_and_return_session,
    _fetch_db_users,
    _fetch_db_groups,
    _fetch_db_properties,
    fetch_db_users,
    fetch_db_groups,
    fetch_db_properties,
)


def sync_production() -> None:
    logger.info("Starting the production sync. See --help for other options.")
    config = get_config_or_exit(required_property='ldap', use_ssl='False',
                                ca_certs_file=None, ca_certs_data=None)
    db_session = establish_and_return_session(config.db_uri)
    connection = establish_and_return_ldap_connection(config=config)
    fetch_and_sync(db_session, connection, config.base_dn, config.required_property)


def sync_fake() -> None:
    logger.info("Starting sync using a mocked LDAP backend. See --help for other options.")
    try:
        db_uri = os.environ['PYCROFT_DB_URI']
    except KeyError:
        logger.critical('PYCROFT_DB_URI not set')
        exit()

    # noinspection PyUnboundLocalVariable
    db_session = establish_and_return_session(db_uri)
    connection = fake_connection()
    BASE_DN = types.DN("ou=pycroft,dc=agdsn,dc=de")

    fetch_and_sync(db_session, connection, BASE_DN)


def fetch_and_sync(
    db_session: Session,
    connection: Connection,
    base_dn: types.DN,
    required_property: str | None = None,
) -> None:
    user_base_dn = types.DN(safe_dn(["ou=users", base_dn]))
    group_base_dn = types.DN(safe_dn(["ou=groups", base_dn]))
    property_base_dn = types.DN(safe_dn(["ou=properties", base_dn]))

    db_users = list(
        fetch_db_users(
            session=db_session,
            base_dn=user_base_dn,
            required_property=required_property,
        )
    )
    logger.info("Fetched %s database users", len(db_users))

    db_groups = list(
        fetch_db_groups(
            session=db_session,
            base_dn=group_base_dn,
            user_base_dn=user_base_dn,
        )
    )
    logger.info("Fetched %s database groups", len(db_groups))

    db_properties = list(
        fetch_db_properties(
            session=db_session,
            base_dn=property_base_dn,
            user_base_dn=user_base_dn,
        )
    )
    logger.info("Fetched %s database properties", len(db_properties))

    ldap_users = list(fetch_ldap_users(connection, base_dn=user_base_dn))
    logger.info("Fetched %s ldap users", len(ldap_users))

    ldap_groups = list(fetch_ldap_groups(connection, base_dn=group_base_dn))
    logger.info("Fetched %s ldap groups", len(ldap_groups))

    ldap_properties = list(fetch_ldap_properties(connection, base_dn=property_base_dn))
    logger.info("Fetched %s ldap properties", len(ldap_properties))

    actions = [
        *bulk_diff_records(
            current_records=ldap_users, desired_records=db_users
        ).values(),
        *bulk_diff_records(
            current_records=ldap_groups, desired_records=db_groups
        ).values(),
        *bulk_diff_records(
            current_records=ldap_properties, desired_records=db_properties
        ).values(),
    ]
    for a in actions:
        execute_real(a, connection)


NAME_LEVEL_MAPPING: dict[str, int] = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL,
}


parser = argparse.ArgumentParser(description="Pycroft ldap syncer")
parser.add_argument('--fake', dest='fake', action='store_true', default=False,
                    help="Use a mocked LDAP backend")
parser.add_argument("-l", "--log", dest='loglevel', type=str,
                    choices=list(NAME_LEVEL_MAPPING.keys()), default='info',
                    help="Set the loglevel")
parser.add_argument("-d", "--debug", dest='loglevel', action='store_const',
                    const='debug', help="Short for --log=debug")


def main() -> int:
    args = parser.parse_args()

    add_stdout_logging(logger, level=NAME_LEVEL_MAPPING[args.loglevel])

    try:
        if args.fake:
            sync_fake()
        else:
            sync_production()
    except KeyboardInterrupt:
        logger.fatal("SIGINT received, stopping.")
        logger.info("Re-run the syncer to retain a consistent state.")
        return 1
    return 0


if __name__ == '__main__':
    exit(main())


def add_stdout_logging(logger: logging.Logger, level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    fmt = logging.Formatter("%(levelname)s %(asctime)s %(name)s %(message)s")
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    logger.setLevel(level)
