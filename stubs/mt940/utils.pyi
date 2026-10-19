import typing as t
import enum

def coalesce(*args): ...

class Strip(enum.IntEnum):
    NONE = t.cast(int, ...)
    LEFT = t.cast(int, ...)
    RIGHT = t.cast(int, ...)
    BOTH = t.cast(int, ...)

def join_lines(string, strip=...): ...
