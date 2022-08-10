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

from .config import get_config_or_exit
from .exporter import sync_all
from ldap_sync.ldap import establish_and_return_ldap_connection, fetch_current_ldap_users, \
    fetch_current_ldap_groups, fetch_current_ldap_properties, fake_connection
from ldap_sync import logger, types
from ldap_sync.db import establish_and_return_session, fetch_users_to_sync, \
    fetch_groups_to_sync, fetch_properties_to_sync


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
    db_users = fetch_users_to_sync(
        session=db_session,
        required_property=required_property,
    )
    logger.info("Fetched %s database users", len(db_users))

    db_groups = fetch_groups_to_sync(db_session)
    logger.info("Fetched %s database groups", len(db_groups))

    db_properties = fetch_properties_to_sync(db_session)
    logger.info("Fetched %s database properties", len(db_properties))

    user_base_dn = types.DN(safe_dn(["ou=users", base_dn]))
    ldap_users = fetch_current_ldap_users(connection, base_dn=user_base_dn)
    logger.info("Fetched %s ldap users", len(ldap_users))

    group_base_dn = types.DN(safe_dn(["ou=groups", base_dn]))
    ldap_groups = fetch_current_ldap_groups(connection, base_dn=group_base_dn)
    logger.info("Fetched %s ldap groups", len(ldap_groups))

    property_base_dn = types.DN(safe_dn(["ou=properties", base_dn]))
    ldap_properties = fetch_current_ldap_properties(
        connection, base_dn=property_base_dn
    )
    logger.info("Fetched %s ldap properties", len(ldap_properties))

    sync_all(connection, ldap_users, db_users, user_base_dn, ldap_groups,
             db_groups, group_base_dn, ldap_properties, db_properties,
             property_base_dn)


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
