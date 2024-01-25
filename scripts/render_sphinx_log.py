from __future__ import annotations
import typing as t
from typing import NamedTuple


class SphinxLog(NamedTuple):
    path: str
    entity: str
    rel_line: str
    level: str
    message: str

    @classmethod
    def from_sphinx_output(cls, line: str) -> t.Self | None:
        args = tuple(el.strip() for el in line.split(":", maxsplit=4))
        if len(args) != 5:
            return None
        return cls(*args)

    def as_gh_annotation(self) -> str:
        title = self.level.capitalize()
        full_msg = f"{self.entity}:{self.rel_line}: {self.message}"
        return f"::{self.level} file={self.path},line=1,title={title}::{full_msg}"


def main():
    import sys

    filename = sys.argv[1]
    with open(filename) as f:
        for line in f.readlines():
            if (l := SphinxLog.from_sphinx_output(line)) is not None:
                print(l.as_gh_annotation())


if __name__ == "__main__":
    main()


try:
    import pytest
except ImportError:
    from unittest.mock import MagicMock

    pytest = MagicMock()


@pytest.mark.parametrize(
    "line,expected",
    [
        (
            "/home/foo/bar.py:docstring of pycroft.lib.user.edit_email:8: "
            "WARNING: Field list ends without a blank line; unexpected unindent.",
            "::WARNING file=/home/foo/bar.py,line=1,title=Warning"
            "::docstring of pycroft.lib.user.edit_email:8: Field list ends without a blank line; unexpected unindent.",
        ),
        (
            "/home/foo/bar.py:docstring of pycroft.lib.user.edit_birthdate:5: "
            "WARNING: Field list ends without a blank line; unexpected unindent.",
            "::WARNING file=/home/foo/bar.py,line=1,title=Warning"
            "::docstring of pycroft.lib.user.edit_birthdate:5: Field list ends without a blank line; unexpected unindent.",
        ),
        (
            "/home/foo/baz.py:docstring of ldap_sync.sources.db._fetch_db_properties:3: "
            "WARNING: undefined label: 'exported_properties'",
            "::WARNING file=/home/foo/baz.py,line=1,title=Warning"
            "::docstring of ldap_sync.sources.db._fetch_db_properties:3: undefined label: 'exported_properties'",
        ),
    ],
)
def test_parsing(line: str, expected: str):
    assert SphinxLog.from_sphinx_output(line).as_gh_annotation() == expected


@pytest.mark.parametrize(
    "line",
    ["this is:too:short", "", "tr ndtrn dtrn", "/home/foo/bar.py:docstring of foo:8:"],
)
def test_parsing_none(line: str):
    assert SphinxLog.from_sphinx_output(line) is None
