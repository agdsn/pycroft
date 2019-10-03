#!/usr/bin/env python3
import logging
import sys
from dataclasses import dataclass

import click

from .connection import get_connection_string, try_create_connection
from .schema import AlembicHelper


@dataclass
class ContextObject:
    alembic_helper: AlembicHelper
    logger: logging.Logger


@click.group()
@click.pass_context
def cli(ctx):
    logger = logging.getLogger('alembic_wrapper')
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler(sys.stdout))

    conn = try_create_connection(get_connection_string(), logger=logger, wait_for_db=False)
    ctx.obj = ContextObject(logger=logger, alembic_helper=AlembicHelper(conn))


assert isinstance(cli, click.Group)


@cli.command()
@click.pass_obj
def current(obj: ContextObject):
    click.echo(obj.alembic_helper.running_version)


@cli.command()
@click.pass_obj
@click.argument('revision')
def upgrade(obj: ContextObject, revision: str):
    obj.alembic_helper.upgrade(revision)


@cli.command()
@click.pass_obj
@click.argument('revision')
def downgrade(obj: ContextObject, revision: str):
    obj.alembic_helper.downgrade(revision)


if __name__ == '__main__':
    cli()
