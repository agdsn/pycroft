from celery import Task
import os

from sqlalchemy.orm import scoped_session, sessionmaker

from pycroft.model import create_engine
from pycroft.model.session import set_scoped_session


class DBTask(Task):
    def run(self, *args, **kwargs):
        pass

    try:
        connection_string = os.environ['PYCROFT_DB_URI']
    except KeyError:
        raise RuntimeError("Environment variable PYCROFT_DB_URI must be "
                           "set to an SQLAlchemy connection string.")

    engine = create_engine(connection_string)
    set_scoped_session(scoped_session(sessionmaker(bind=engine)))
