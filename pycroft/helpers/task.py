"""
pycroft.helpers.task
~~~~~~~~~~~~~~~~~~~~
"""
import logging
import os
import sys
import typing as t

from celery import Task
from sqlalchemy.orm import scoped_session, sessionmaker, Session

from pycroft.model.session import set_scoped_session, session
from scripts.connection import get_connection_string, try_create_connection


class DBTask(Task):
    """
    Base class for tasks which use the database.
    """

    connection = None
    engine = None

    def run(self, *args: t.Any, **kwargs: t.Any) -> None:
        pass

    def after_return(
        self,
        status: str,
        retval: t.Any,
        task_id: str,
        args: tuple,
        kwargs: dict,
        einfo: t.Any = None,
    ) -> None:
        session.close()

    def __init__(self) -> None:
        in_celery = sys.argv and sys.argv[0].endswith("celery") and "worker" in sys.argv
        if not in_celery:
            return
        try:
            connection_string = os.environ["PYCROFT_DB_URI"]
        except KeyError:
            raise RuntimeError(
                "Environment variable PYCROFT_DB_URI must be "
                "set to an SQLAlchemy connection string."
            )

        self.connection, self.engine = try_create_connection(
            connection_string, 5, logger=logging.getLogger("tasks"), echo=False
        )

        set_scoped_session(
            t.cast(Session, scoped_session(sessionmaker(bind=self.engine)))
        )

    def __del__(self) -> None:
        if self.connection is not None:
            self.connection.close()
