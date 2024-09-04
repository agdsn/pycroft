#!/usr/bin/env python3
import logging
import sys
from dataclasses import dataclass

import click
from alembic import command
from alembic.config import Config
from pycroft.model.alembic import get_alembic_config

from .connection import get_connection_string, try_create_connection


@dataclass
class ContextObject:
    alembic_cfg: Config
    logger: logging.Logger


@click.group()
@click.pass_context
@click.option('--verbose', '-v', is_flag=True,
              help="Verbose, i.e. create the connection with `echo=True`")
def cli(ctx, verbose: bool):
    logger = logging.getLogger('alembic_wrapper')
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler(sys.stdout))

    conn, engine = try_create_connection(get_connection_string(), logger=logger, wait_for_db=False,
                                 echo=verbose)
    ctx.obj = ContextObject(
        logger=logger,
        alembic_cfg=get_alembic_config(),
    )


assert isinstance(cli, click.Group)


@cli.command(help=command.current.__doc__)
@click.pass_obj
def current(obj: ContextObject):
    command.current(obj.alembic_cfg)


@cli.command(help=command.upgrade.__doc__)
@click.pass_obj
@click.argument('revision')
def upgrade(obj: ContextObject, revision: str):
    command.upgrade(obj.alembic_cfg, revision)


@cli.command(help=command.downgrade.__doc__)
@click.pass_obj
@click.argument('revision')
def downgrade(obj: ContextObject, revision: str):
    command.downgrade(obj.alembic_cfg, revision)


@cli.command(help=command.stamp.__doc__)
@click.pass_obj
@click.argument("revision")
def stamp(obj: ContextObject, revision: str):
    command.stamp(obj.alembic_cfg, revision)


@cli.command(help=command.stamp.__doc__)
@click.pass_obj
@click.option("-m", "--message", "message")
@click.option("--autogenerate", is_flag=True, default=False)
def revision(obj: ContextObject, message: str, autogenerate: bool):
    command.revision(obj.alembic_cfg, message=message, autogenerate=autogenerate)


if __name__ == '__main__':
    cli()
