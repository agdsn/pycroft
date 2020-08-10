import logging

from celery import Task
from sqlalchemy.orm import scoped_session, sessionmaker

from pycroft.model.session import set_scoped_session, session
from scripts.connection import get_connection_string, try_create_connection


class DBTask(Task):
    """
    Base class for tasks which use the database.
    """

    def run(self, *args, **kwargs):
        pass

    def after_return(self, status, retval, task_id, args, kwargs, einfo=None):
        session.close()

    def __init__(self):
        connection_string = get_connection_string()

        self.connection, self.engine = try_create_connection(connection_string,
                                                  5,
                                                  logger=logging.getLogger("tasks"),
                                                  echo=False)

        set_scoped_session(scoped_session(sessionmaker(bind=self.engine)))

    def __del__(self):
        self.connection.close()
