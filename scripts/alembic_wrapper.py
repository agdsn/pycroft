#!/usr/bin/env python3
import logging
import sys
import typing as t
from dataclasses import dataclass

import click
from alembic import command
from alembic import autogenerate as autogen
from alembic.migration import MigrationContext
from alembic.config import Config
from rich import print
from rich.console import RenderableType
from rich.table import Table
from rich.text import Text
from sqlalchemy import Connection

from pycroft.model.alembic import get_alembic_config
from pycroft.model.base import ModelBase

from .connection import get_connection_string, try_create_connection


@dataclass
class ContextObject:
    alembic_cfg: Config
    conn: Connection
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
        conn=conn,
        logger=logger,
        alembic_cfg=get_alembic_config(),
    )


assert isinstance(cli, click.Group)


@cli.command(help=command.current.__doc__)
@click.pass_obj
def current(obj: ContextObject):
    command.current(obj.alembic_cfg)


@cli.command(help=command.check.__doc__)
@click.pass_obj
def check(obj: ContextObject):
    command.check(obj.alembic_cfg)


@cli.command()
@click.pass_obj
def diff(obj: ContextObject):
    # https://alembic.sqlalchemy.org/en/latest/api/autogenerate.html#getting-diffs
    migration_context = MigrationContext.configure(obj.conn)
    metadata = ModelBase.metadata
    print(render_diffset(autogen.compare_metadata(migration_context, metadata)))


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


@cli.command(help=command.revision.__doc__)
@click.pass_obj
@click.option("-m", "--message", "message")
@click.option("--autogenerate", is_flag=True, default=False)
def revision(obj: ContextObject, message: str, autogenerate: bool):
    command.revision(obj.alembic_cfg, message=message, autogenerate=autogenerate)


def render_diffset(diffs) -> t.Iterator[tuple[t.Any, ...]]:
    table = Table(show_header=False, box=None)
    for diff in diffs:
        table.add_row(*render_diff_tuple(diff))
    return table


def render_diff_tuple(diff_tuple) -> tuple[RenderableType, RenderableType]:

    diff_op, *rest = diff_tuple

    if isinstance(diff_op, tuple):
        assert not rest
        diff_op, *rest = diff_op

    if not rest:
        col2 = ""
    else:
        obj, *extra = rest
        if obj is not None:
            col2 = Text.from_markup(f"[bold]{obj}[/] {extra!r}")
        else:
            col2 = Text.from_markup(f"{extra!r}")

    return render_diff_op(diff_op), col2


def render_diff_op(diff_op: str) -> Text:
    if op := try_strip(diff_op, "add_"):
        return Text.from_markup(f"[bold green]+{op}[/]")
    elif op := try_strip(diff_op, "remove_"):
        return Text.from_markup(f"[bold red]-{op}[/]")
    elif op := try_strip(diff_op, "modify_"):
        return Text.from_markup(f"[bold blue]~{op}[/]")
    else:
        return Text.from_markup(f"[bold yellow]`{diff_op}`[/]")


def try_strip(string: str, prefix: str) -> str | None:
    if string.startswith(prefix):
        return string.removeprefix(prefix)
    return None


if __name__ == '__main__':
    cli()
