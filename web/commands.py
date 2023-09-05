#  Copyright (c) 2021. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
import typing as t
import os

import click
from flask import Flask

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
        with engine.connect() as connection:
            drop_db_model(bind=connection)
