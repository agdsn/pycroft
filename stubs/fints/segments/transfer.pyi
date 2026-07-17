from .base import FinTS3Segment as FinTS3Segment, ParameterSegment as ParameterSegment
from _typeshed import Incomplete
from fints.fields import (
    DataElementField as DataElementField,
    DataElementGroupField as DataElementGroupField,
)
from fints.formals import (
    Amount1 as Amount1,
    BatchTransferParameter1 as BatchTransferParameter1,
    KTI1 as KTI1,
)

class HKCCS1(FinTS3Segment):
    account: Incomplete
    sepa_descriptor: Incomplete
    sepa_pain_message: Incomplete

class HKIPZ1(FinTS3Segment):
    account: Incomplete
    sepa_descriptor: Incomplete
    sepa_pain_message: Incomplete

class HKCCM1(FinTS3Segment):
    account: Incomplete
    sum_amount: Incomplete
    request_single_booking: Incomplete
    sepa_descriptor: Incomplete
    sepa_pain_message: Incomplete

class HKIPM1(FinTS3Segment):
    account: Incomplete
    sum_amount: Incomplete
    request_single_booking: Incomplete
    sepa_descriptor: Incomplete
    sepa_pain_message: Incomplete

class HICCMS1(ParameterSegment):
    parameter: Incomplete
