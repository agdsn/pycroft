#!/usr/bin/env python3
from importlib.resources import files
import logging
import typing as t

import click
from alembic import autogenerate as autogen
from alembic.migration import MigrationContext
from alembic.config import Config, CommandLine
from rich.console import RenderableType
from rich.table import Table
from rich.text import Text

from pycroft.model.base import ModelBase

from .connection import get_connection_string, try_create_connection

logger = logging.getLogger(__name__)

@click.command(
    name="alembic",
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
    add_help_option=False,
)
@click.pass_context
def main(ctx: click.Context):
    cli = CommandLine()
    cli.register_command(diff)
    ini_location = str(files("pycroft.model").joinpath("alembic.ini"))
    cli.main(["-c", ini_location, *ctx.args])


def diff(config: Config, *args: t.Any, **kwargs: t.Any) -> None:
    """Produce a diff of the code-defined schema and actual schema."""
    conn, _ = try_create_connection(
        get_connection_string(), logger=logger, wait_for_db=False, echo=False
    )
    migration_context = MigrationContext.configure(conn)
    metadata = ModelBase.metadata
    diff_table = render_diffset(autogen.compare_metadata(migration_context, metadata))
    from rich import print
    print(diff_table)


def render_diffset(diffs) -> Table:
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
    main()
