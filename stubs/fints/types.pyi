from .exceptions import FinTSNoResponseError as FinTSNoResponseError
from .utils import SubclassesMixin as SubclassesMixin
from _typeshed import Incomplete
from collections.abc import Generator

class Field:
    length: Incomplete
    min_length: Incomplete
    max_length: Incomplete
    count: Incomplete
    min_count: Incomplete
    max_count: Incomplete
    required: Incomplete
    __doc__: Incomplete
    def __init__(
        self,
        length: Incomplete | None = None,
        min_length: Incomplete | None = None,
        max_length: Incomplete | None = None,
        count: Incomplete | None = None,
        min_count: Incomplete | None = None,
        max_count: Incomplete | None = None,
        required: bool = True,
        _d: Incomplete | None = None,
    ) -> None: ...
    def __get__(self, instance, owner): ...
    def __set__(self, instance, value) -> None: ...
    def __delete__(self, instance) -> None: ...
    def render(self, value): ...

class TypedField(Field, SubclassesMixin):
    def __new__(cls, *args, **kwargs): ...
    type: Incomplete
    def __init__(self, type: Incomplete | None = None, *args, **kwargs) -> None: ...

class ValueList:
    def __init__(self, parent) -> None: ...
    def __getitem__(self, i): ...
    def __setitem__(self, i, value) -> None: ...
    def __delitem__(self, i) -> None: ...
    def __len__(self) -> int: ...
    def __iter__(self): ...
    def print_nested(
        self,
        stream: Incomplete | None = None,
        level: int = 0,
        indent: str = "    ",
        prefix: str = "",
        first_level_indent: bool = True,
        trailer: str = "",
        print_doc: bool = True,
        first_line_suffix: str = "",
    ) -> None: ...

class SegmentSequence:
    segments: Incomplete
    def __init__(self, segments: Incomplete | None = None) -> None: ...
    def render_bytes(self) -> bytes: ...
    def print_nested(
        self,
        stream: Incomplete | None = None,
        level: int = 0,
        indent: str = "    ",
        prefix: str = "",
        first_level_indent: bool = True,
        trailer: str = "",
        print_doc: bool = True,
        first_line_suffix: str = "",
    ) -> None: ...
    def find_segments(
        self,
        query: Incomplete | None = None,
        version: Incomplete | None = None,
        callback: Incomplete | None = None,
        recurse: bool = True,
        throw: bool = False,
    ) -> Generator[Incomplete, None, Incomplete]: ...
    def find_segment_first(self, *args, **kwargs): ...
    def find_segment_highest_version(
        self,
        query: Incomplete | None = None,
        version: Incomplete | None = None,
        callback: Incomplete | None = None,
        recurse: bool = True,
        default: Incomplete | None = None,
    ): ...

class ContainerMeta(type):
    @classmethod
    def __prepare__(metacls, name, bases): ...
    def __new__(cls, name, bases, classdict): ...

class Container(metaclass=ContainerMeta):
    def __init__(self, *args, **kwargs) -> None: ...
    @classmethod
    def naive_parse(cls, data): ...
    def is_unset(self): ...
    def print_nested(
        self,
        stream: Incomplete | None = None,
        level: int = 0,
        indent: str = "    ",
        prefix: str = "",
        first_level_indent: bool = True,
        trailer: str = "",
        print_doc: bool = True,
        first_line_suffix: str = "",
    ) -> None: ...
