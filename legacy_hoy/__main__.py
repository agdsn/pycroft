import argparse
import logging as std_logging
import os
from .import_hoy import log, import_hoy

parser = argparse.ArgumentParser(
    prog='import_hoy', description='-')
parser.add_argument("-l", "--log", dest="log_level",
    choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
    default='INFO')


def main():
    args = parser.parse_args()

    import_log_fname = "import.log"
    sqlalchemy_log_fname = "import.sqlalchemy.log"

    log.info("Logging to %s and %s" % (import_log_fname, sqlalchemy_log_fname))

    log_fmt = '[%(levelname).4s] %(name)s:%(funcName)s:%(message)s'
    formatter = std_logging.Formatter(log_fmt)
    std_logging.basicConfig(level=std_logging.DEBUG,
                            format=log_fmt,
                            filename=import_log_fname,
                            filemode='w')
    console = std_logging.StreamHandler()
    console.setLevel(getattr(std_logging, args.log_level))
    console.setFormatter(formatter)
    std_logging.getLogger('').addHandler(console)

    sqlalchemy_loghandler = std_logging.FileHandler(sqlalchemy_log_fname)
    std_logging.getLogger('sqlalchemy').addHandler(sqlalchemy_loghandler)
    sqlalchemy_loghandler.setLevel(std_logging.DEBUG)
    import_hoy(os.environ['PYCROFT_DB_URI'])
    log.info("Import finished.")
    return 0


if __name__ == '__main__':
    exit(main())
