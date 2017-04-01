import argparse
import logging
import os

from .exporter import add_stdout_logging, establish_and_return_ldap_connection, \
     establish_and_return_session, fake_connection, fetch_current_ldap_users, \
     fetch_users_to_sync, get_config_or_exit, logger, sync_all


logger = logging.getLogger('ldap_sync')


def main():
    logger.info("Starting the production sync. See --help for other options.")
    config = get_config_or_exit()

    db_users = fetch_users_to_sync(
        session=establish_and_return_session(config.db_uri)
    )
    logger.info("Fetched %s database users", len(db_users))

    connection = establish_and_return_ldap_connection(
        host=config.host,
        port=config.port,
        bind_dn=config.bind_dn,
        bind_pw=config.bind_pw,
    )

    ldap_users = fetch_current_ldap_users(connection, base_dn=config.base_dn)
    logger.info("Fetched %s ldap users", len(ldap_users))

    sync_all(db_users, ldap_users, connection, base_dn=config.base_dn)


def main_fake_ldap():
    logger.info("Starting sync using a mocked LDAP backend. See --help for other options.")
    try:
        db_uri = os.environ['PYCROFT_DB_URI']
    except KeyError:
        logger.critical('PYCROFT_DB_URI not set')
        exit()

    db_users = fetch_users_to_sync(
        session=establish_and_return_session(db_uri)
    )
    logger.info("Fetched %s database users", len(db_users))

    connection = fake_connection()
    BASE_DN = 'ou=users,dc=agdsn,dc=de'
    logger.debug("BASE_DN set to %s", BASE_DN)

    ldap_users = fetch_current_ldap_users(connection, base_dn=BASE_DN)
    logger.info("Fetched %s ldap users", len(ldap_users))

    sync_all(db_users, ldap_users, connection, base_dn=BASE_DN)


NAME_LEVEL_MAPPING = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL,
}


parser = argparse.ArgumentParser(description="Pycroft ldap syncer")
parser.add_argument('--fake', dest='fake', action='store_true',
                    help="Use a mocked LDAP backend")
group_log = parser.add_mutually_exclusive_group()
group_log.add_argument("-l", "--log", dest='loglevel', type=str,
                       choices=list(NAME_LEVEL_MAPPING.keys()),
                       help="Set the loglevel")
group_log.add_argument("-d", "--debug", dest='debug', action='store_true',
                       help="Short for --log=debug")
parser.set_defaults(fake=False, loglevel='info')

args = parser.parse_args()
if args.debug:
    args.loglevel = 'debug'

add_stdout_logging(logger, level=NAME_LEVEL_MAPPING[args.loglevel])


if args.fake:
    main_fake_ldap()
else:
    main()
