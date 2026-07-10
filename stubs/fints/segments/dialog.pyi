from ..fields import (
    CodeField as CodeField,
    DataElementField as DataElementField,
    DataElementGroupField as DataElementGroupField,
)
from ..formals import Response as Response, SynchronizationMode as SynchronizationMode
from .base import FinTS3Segment as FinTS3Segment
from _typeshed import Incomplete

class HKSYN3(FinTS3Segment):
    synchronization_mode: Incomplete

class HISYN4(FinTS3Segment):
    system_id: Incomplete
    message_number: Incomplete
    security_reference_signature_key: Incomplete
    security_reference_digital_signature: Incomplete

class HKEND1(FinTS3Segment):
    dialog_id: Incomplete

class HIRMG2(FinTS3Segment):
    responses: Incomplete

class HIRMS2(FinTS3Segment):
    responses: Incomplete
