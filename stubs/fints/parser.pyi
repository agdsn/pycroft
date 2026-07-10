from .formals import (
    Container as Container,
    DataElementGroupField as DataElementGroupField,
    SegmentSequence as SegmentSequence,
    ValueList as ValueList,
)
from .segments import (
    accounts as accounts,
    auth as auth,
    bank as bank,
    base as base,
    debit as debit,
    depot as depot,
    dialog as dialog,
    journal as journal,
    message as message,
    saldo as saldo,
    statement as statement,
    transfer as transfer,
)
from .segments.base import FinTS3Segment as FinTS3Segment
from _typeshed import Incomplete
from enum import Enum

robust_mode: bool

class FinTSParserWarning(UserWarning): ...
class FinTSParserError(ValueError): ...

TOKEN_RE: Incomplete

class Token(Enum):
    EOF = "eof"
    CHAR = "char"
    BINARY = "bin"
    PLUS = "+"
    COLON = ":"
    APOSTROPHE = "'"

class ParserState:
    def __init__(
        self,
        data: bytes,
        start: int = 0,
        end: Incomplete | None = None,
        encoding: str = "iso-8859-1",
    ) -> None: ...
    def peek(self): ...
    def consume(self, token: Incomplete | None = None): ...

class FinTS3Parser:
    def parse_message(self, data: bytes) -> SegmentSequence: ...
    def parse_segment(self, segment): ...
    def parse_deg_noniter(self, clazz, data, required): ...
    def parse_deg(self, clazz, data_i, required: bool = True): ...
    @staticmethod
    def explode_segments(data: bytes, start: int = 0, end: Incomplete | None = None): ...

class FinTS3Serializer:
    def serialize_message(self, message: SegmentSequence) -> bytes: ...
    def serialize_segment(self, segment): ...
    def serialize_deg(self, deg, allow_skip: bool = False): ...
    @staticmethod
    def implode_segments(message: list): ...
    @staticmethod
    def escape_value(val): ...
