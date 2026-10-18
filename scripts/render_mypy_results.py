from __future__ import annotations

import re
import typing as t
from typing import NamedTuple

RE_OUTPUT_LINE = re.compile(
    r"^(?P<file>.+?):(?P<line>\d+)(?::(?P<col>\d+))?: (?P<severity>[a-z]+): (?P<message>.*)$"
)


class MypyMessage(NamedTuple):
    file: str
    line: str
    severity: str
    message: str
    col: str | None = None

    @classmethod
    def from_mypy_output(cls, output: str) -> t.Self | None:
        match = RE_OUTPUT_LINE.match(output)
        if match is None:
            return None
        # TODO support optional ` [error-code]` at end of line
        return cls(
            file=match["file"],
            line=match["line"],
            severity=match["severity"],
            message=match["message"],
            col=match["col"],
        )

    def as_gh_annotation(self) -> str:
        title = self.severity.capitalize()
        loc = f"file={self.file},line={self.line}"
        if self.col is not None:
            loc += f",col={self.col}"
        return f"::{self.severity} {loc},title={title}::{self.message}"


def main():
    import sys

    filename = sys.argv[1]
    with open(filename) as f:
        for line in f.readlines():
            if (m := MypyMessage.from_mypy_output(line)) is not None:
                print(m.as_gh_annotation())


if __name__ == "__main__":
    main()
