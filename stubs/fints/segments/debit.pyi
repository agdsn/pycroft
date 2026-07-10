from ..fields import (
    CodeField as CodeField,
    DataElementField as DataElementField,
    DataElementGroupField as DataElementGroupField,
)
from ..formals import (
    Amount1 as Amount1,
    KTI1 as KTI1,
    QueryScheduledBatchDebitParameter1 as QueryScheduledBatchDebitParameter1,
    QueryScheduledDebitParameter1 as QueryScheduledDebitParameter1,
    QueryScheduledDebitParameter2 as QueryScheduledDebitParameter2,
    SEPACCode1 as SEPACCode1,
    ScheduledBatchDebitParameter1 as ScheduledBatchDebitParameter1,
    ScheduledBatchDebitParameter2 as ScheduledBatchDebitParameter2,
    ScheduledCOR1BatchDebitParameter1 as ScheduledCOR1BatchDebitParameter1,
    ScheduledCOR1DebitParameter1 as ScheduledCOR1DebitParameter1,
    ScheduledDebitParameter1 as ScheduledDebitParameter1,
    ScheduledDebitParameter2 as ScheduledDebitParameter2,
    StatusSEPATask1 as StatusSEPATask1,
    SupportedSEPAPainMessages1 as SupportedSEPAPainMessages1,
)
from .base import FinTS3Segment as FinTS3Segment, ParameterSegment as ParameterSegment
from _typeshed import Incomplete

class BatchDebitBase(FinTS3Segment):
    account: Incomplete
    sum_amount: Incomplete
    request_single_booking: Incomplete
    sepa_descriptor: Incomplete
    sepa_pain_message: Incomplete

class DebitResponseBase(FinTS3Segment):
    task_id: Incomplete

class HKDSE1(FinTS3Segment):
    account: Incomplete
    sepa_descriptor: Incomplete
    sepa_pain_message: Incomplete

class HIDSE1(DebitResponseBase): ...

class HIDSES1(ParameterSegment):
    parameter: Incomplete

class HKDSE2(FinTS3Segment):
    account: Incomplete
    sepa_descriptor: Incomplete
    sepa_pain_message: Incomplete

class HIDSE2(DebitResponseBase): ...

class HIDSES2(ParameterSegment):
    parameter: Incomplete

class HKDME1(BatchDebitBase): ...
class HIDME1(DebitResponseBase): ...

class HIDMES1(ParameterSegment):
    parameter: Incomplete

class HKDME2(BatchDebitBase): ...
class HIDME2(DebitResponseBase): ...

class HIDMES2(ParameterSegment):
    parameter: Incomplete

class HKDSC1(FinTS3Segment):
    account: Incomplete
    sepa_descriptor: Incomplete
    sepa_pain_message: Incomplete

class HIDSC1(DebitResponseBase): ...

class HIDSCS1(ParameterSegment):
    parameter: Incomplete

class HKDMC1(BatchDebitBase): ...
class HIDMC1(DebitResponseBase): ...

class HIDMCS1(ParameterSegment):
    parameter: Incomplete

class HKDBS1(FinTS3Segment):
    account: Incomplete
    supported_sepa_pain_messages: Incomplete
    date_start: Incomplete
    date_end: Incomplete
    max_number_responses: Incomplete
    touchdown_point: Incomplete

class HIDBS1(FinTS3Segment):
    account: Incomplete
    sepa_descriptor: Incomplete
    sepa_pain_message: Incomplete
    task_id: Incomplete
    task_cancelable: Incomplete
    task_changeable: Incomplete

class HIDBSS1(ParameterSegment):
    parameter: Incomplete

class HKDBS2(FinTS3Segment):
    account: Incomplete
    supported_sepa_pain_messages: Incomplete
    date_start: Incomplete
    date_end: Incomplete
    max_number_responses: Incomplete
    touchdown_point: Incomplete

class HIDBS2(FinTS3Segment):
    account: Incomplete
    sepa_descriptor: Incomplete
    sepa_pain_message: Incomplete
    task_id: Incomplete
    sepa_c_code: Incomplete
    task_changeable: Incomplete
    status_sepa_task: Incomplete

class HIDBSS2(ParameterSegment):
    parameter: Incomplete

class HKDMB1(FinTS3Segment):
    account: Incomplete
    date_start: Incomplete
    date_end: Incomplete
    max_number_responses: Incomplete
    touchdown_point: Incomplete

class HIDMB1(FinTS3Segment):
    task_id: Incomplete
    account: Incomplete
    date_entered: Incomplete
    date_booked: Incomplete
    debit_count: Incomplete
    sum_amount: Incomplete

class HIDMBS1(ParameterSegment):
    parameter: Incomplete
