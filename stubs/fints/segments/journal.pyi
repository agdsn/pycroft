from .base import (
    FinTS3Segment as FinTS3Segment,
    ParameterSegment as ParameterSegment,
    ParameterSegment_22 as ParameterSegment_22,
)
from _typeshed import Incomplete
from fints.fields import (
    DataElementField as DataElementField,
    DataElementGroupField as DataElementGroupField,
)
from fints.formals import ReferenceMessage as ReferenceMessage, Response as Response

class HKPRO3(FinTS3Segment):
    date_start: Incomplete
    date_end: Incomplete
    max_number_responses: Incomplete
    touchdown_point: Incomplete

class HIPRO3(FinTS3Segment):
    reference_message: Incomplete
    reference: Incomplete
    date: Incomplete
    time: Incomplete
    responses: Incomplete

class HIPROS3(ParameterSegment_22): ...

class HKPRO4(FinTS3Segment):
    date_start: Incomplete
    date_end: Incomplete
    max_number_responses: Incomplete
    touchdown_point: Incomplete

class HIPRO4(FinTS3Segment):
    reference_message: Incomplete
    reference: Incomplete
    date: Incomplete
    time: Incomplete
    responses: Incomplete

class HIPROS4(ParameterSegment): ...
