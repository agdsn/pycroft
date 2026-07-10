import threading
from .models import Holding as Holding
from _typeshed import Incomplete
from collections.abc import Generator
from enum import Enum
from enum_tools import document_enum
from typing import override

def mt940_to_array(data): ...
def classproperty(f): ...
def compress_datablob(magic: bytes, version: int, data: dict): ...
def decompress_datablob(magic: bytes, blob: bytes, obj: object = None): ...

class SubclassesMixin: ...

class DocTypeMixin:
    __doc__: str
    def __init__(self, *args, **kwargs) -> None: ...

class FieldRenderFormatStringMixin: ...

class FixedLengthMixin:
    def __init__(self, *args, **kwargs) -> None: ...

class ShortReprMixin:
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

class MT535_Miniparser:
    re_identification: Incomplete
    re_marketprice: Incomplete
    re_pricedate: Incomplete
    re_pieces: Incomplete
    re_totalvalue: Incomplete
    re_acquisitionprice: Incomplete
    def parse(self, lines): ...
    def collapse_multilines(self, lines): ...
    def grab_financial_instrument_segments(self, clauses): ...

class Password(str):
    protected: bool
    value: Incomplete
    blocked: bool
    def __init__(self, value) -> None: ...
    @classmethod
    def protect(cls) -> Generator[None, None, None]: ...
    def block(self) -> None: ...
    @override
    def __add__(self, other): ...
    @override
    def replace(self, *args, **kwargs): ...

class RepresentableEnum(Enum): ...

def minimal_interactive_cli_bootstrap(client) -> None: ...

class LogConfiguration(threading.local):
    reduced: Incomplete
    def __init__(self, reduced: bool = False) -> None: ...
    @staticmethod
    def set(reduced: bool = False) -> None: ...
    @staticmethod
    def changed(reduced: bool = False) -> Generator[None, None, None]: ...

log_configuration: Incomplete
doc_enum = document_enum

def decode_phototan_image(data): ...
