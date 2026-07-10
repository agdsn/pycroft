from .base import FinTS3Segment as FinTS3Segment
from _typeshed import Incomplete
from fints.fields import (
    DataElementField as DataElementField,
    DataElementGroupField as DataElementGroupField,
)
from fints.formals import Account2 as Account2, Account3 as Account3

class HKWPD5(FinTS3Segment):
    account: Incomplete
    currency: Incomplete
    quality: Incomplete
    max_number_responses: Incomplete
    touchdown_point: Incomplete

class HIWPD5(FinTS3Segment):
    holdings: Incomplete

class HKWPD6(FinTS3Segment):
    account: Incomplete
    currency: Incomplete
    quality: Incomplete
    max_number_responses: Incomplete
    touchdown_point: Incomplete

class HIWPD6(FinTS3Segment):
    holdings: Incomplete
