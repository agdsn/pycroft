import typing as t
from importlib import resources

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Connection

import pycroft


def get_alembic_config() -> Config:
    Config(resources.files(pycroft.model) / "alembic.ini")


class SchemaState(t.NamedTuple):
    running_version: str
    desired_version: str


def determine_schema_state(connection: Connection) -> SchemaState:
    cfg = get_alembic_config()
    return SchemaState(
        MigrationContext.configure(connection=connection).get_current_revision(),
        ScriptDirectory.from_config(cfg).get_current_head(),
    )
