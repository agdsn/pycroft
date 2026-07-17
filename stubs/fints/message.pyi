from .formals import SegmentSequence as SegmentSequence
from .segments.base import FinTS3Segment as FinTS3Segment
from .segments.dialog import HIRMS2 as HIRMS2
from _typeshed import Incomplete
from collections.abc import Generator
from enum import Enum

class MessageDirection(Enum):
    FROM_CUSTOMER = 1
    FROM_INSTITUTE = 2

class FinTSMessage(SegmentSequence):
    DIRECTION: Incomplete
    dialog: Incomplete
    next_segment_number: int
    def __init__(self, dialog: Incomplete | None = None, *args, **kwargs) -> None: ...
    def __iadd__(self, segment: FinTS3Segment): ...
    def response_segments(self, ref, *args, **kwargs) -> Generator[Incomplete, None, None]: ...
    def responses(
        self, ref, code: Incomplete | None = None
    ) -> Generator[Incomplete, None, None]: ...

class FinTSCustomerMessage(FinTSMessage):
    DIRECTION: Incomplete

class FinTSInstituteMessage(FinTSMessage):
    DIRECTION: Incomplete
