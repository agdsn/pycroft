from .base import FinTS3Segment as FinTS3Segment
from _typeshed import Incomplete
from fints.fields import (
    DataElementField as DataElementField,
    DataElementGroupField as DataElementGroupField,
)
from fints.formals import (
    Account2 as Account2,
    Account3 as Account3,
    Amount1 as Amount1,
    Balance1 as Balance1,
    Balance2 as Balance2,
    KTI1 as KTI1,
    Timestamp1 as Timestamp1,
)

class HKSAL5(FinTS3Segment):
    account: Incomplete
    all_accounts: Incomplete
    max_number_responses: Incomplete
    touchdown_point: Incomplete

class HISAL5(FinTS3Segment):
    account: Incomplete
    account_product: Incomplete
    currency: Incomplete
    balance_booked: Incomplete
    balance_pending: Incomplete
    line_of_credit: Incomplete
    available_amount: Incomplete
    used_amount: Incomplete
    booking_date: Incomplete
    booking_time: Incomplete
    date_due: Incomplete

class HKSAL6(FinTS3Segment):
    account: Incomplete
    all_accounts: Incomplete
    max_number_responses: Incomplete
    touchdown_point: Incomplete

class HISAL6(FinTS3Segment):
    account: Incomplete
    account_product: Incomplete
    currency: Incomplete
    balance_booked: Incomplete
    balance_pending: Incomplete
    line_of_credit: Incomplete
    available_amount: Incomplete
    used_amount: Incomplete
    overdraft: Incomplete
    booking_timestamp: Incomplete
    date_due: Incomplete

class HKSAL7(FinTS3Segment):
    account: Incomplete
    all_accounts: Incomplete
    max_number_responses: Incomplete
    touchdown_point: Incomplete

class HISAL7(FinTS3Segment):
    account: Incomplete
    account_product: Incomplete
    currency: Incomplete
    balance_booked: Incomplete
    balance_pending: Incomplete
    line_of_credit: Incomplete
    available_amount: Incomplete
    used_amount: Incomplete
    overdraft: Incomplete
    booking_timestamp: Incomplete
    date_due: Incomplete
