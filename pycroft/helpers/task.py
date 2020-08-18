import logging

from celery import Task
from sqlalchemy.orm import scoped_session, sessionmaker

from pycroft.model.session import set_scoped_session, session
from scripts.connection import get_connection_string, try_create_connection


class DBTask(Task):
    """
    Base class for tasks which use the database.
    """

    connection = None

    def __call__(self, *args, **kwargs):
        connection_string = get_connection_string()

        self.connection, self.engine = try_create_connection(connection_string,
                                                             5,
                                                             logger=logging.getLogger("tasks"),
                                                             echo=False)

        set_scoped_session(scoped_session(sessionmaker(bind=self.engine)))

        return self.run(*args, **kwargs)

    def run(self, *args, **kwargs):
        pass

    def after_return(self, status, retval, task_id, args, kwargs, einfo=None):
        session.close()

    def __del__(self):
        if self.connection is not None:
            self.connection.close()
