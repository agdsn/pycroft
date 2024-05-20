#  Copyright (c) 2021. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
import typing as t
import os
from importlib import resources

import click
from alembic.config import Config
from alembic import command
from flask import Flask

import pycroft
from pycroft.model import create_db_model
from pycroft.model import create_engine, drop_db_model


def register_commands(app: Flask) -> None:
    """Register custom commands executable via `flask $command_name`."""

    cli = t.cast(click.Group, app.cli)

    @cli.command("create-model", help="Create the database model.")
    def create_model() -> None:
        engine = create_engine(os.getenv('PYCROFT_DB_URI'))
        with engine.begin() as connection:
            create_db_model(bind=connection)

    @cli.command("drop-model", help="Drop the database model.")
    def drop_model() -> None:
        engine = create_engine(os.getenv('PYCROFT_DB_URI'))
        click.confirm(f'This will drop the whole database schema associated to {engine!r}.'
                      ' Are you absolutely sure?', abort=True)
        with engine.begin() as connection:
            drop_db_model(bind=connection)

    @cli.command("migrate", help="Apply the latest migrations (`alembic upgrade head`)")
    def upgrade_schema() -> None:
        engine = create_engine(os.getenv("PYCROFT_DB_URI"))
        config_path = resources.files(pycroft.model) / "alembic.ini"
        app.logger.info("using alembic config %r", config_path)
        alembic_cfg = Config(config_path)

        app.logger.info("> alembic upgrade head…")
        with engine.begin() as conn:
            alembic_cfg.attributes["connection"] = conn
            command.upgrade(alembic_cfg, "head")
        app.logger.info("…done ")
