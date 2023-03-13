import enum

def coalesce(*args): ...

class Strip(enum.IntEnum):
    NONE: int
    LEFT: int
    RIGHT: int
    BOTH: int

def join_lines(string, strip=...): ...
