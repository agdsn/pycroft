import logging

from celery import Task
from sqlalchemy.orm import scoped_session, sessionmaker

from pycroft.model.session import set_scoped_session, session
from scripts.connection import get_connection_string, try_create_connection


class DBTask(Task):
    """
    Base class for tasks which use the database.
    """

    engine = None

    def __init__(self, *args, **kwargs):
        if self.engine is None:
            print("Created engine")

            connection_string = get_connection_string()

            _, self.engine = try_create_connection(connection_string,
                                                   5,
                                                   logger=logging.getLogger("tasks"),
                                                   echo=False)

            set_scoped_session(scoped_session(sessionmaker(bind=self.engine)))

    def run(self, *args, **kwargs):
        pass
