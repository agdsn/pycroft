import enum
from . import models as models
from _typeshed import Incomplete


logger: Incomplete

class Tag:
    id: int | str
    RE_FLAGS: Incomplete
    scope: Incomplete
    re: Incomplete
    def __init__(self) -> None: ...
    def parse(self, transactions, value): ...
    def __call__(self, transactions, value): ...
    def __new__(cls, *args, **kwargs): ...
    def __hash__(self): ...

class DateTimeIndication(Tag):
    pattern: str
    def __call__(self, transactions, value): ...

class TransactionReferenceNumber(Tag):
    pattern: str

class RelatedReference(Tag):
    pattern: str

class AccountIdentification(Tag):
    pattern: str

class StatementNumber(Tag):
    pattern: str

class FloorLimitIndicator(Tag):
    pattern: str
    def __call__(self, transactions, value): ...

class NonSwift(Tag):
    class scope(models.Transaction, models.Transactions): ...
    pattern: str
    sub_pattern: str
    sub_pattern_m: Incomplete
    def __call__(self, transactions, value): ...

class BalanceBase(Tag):
    pattern: str
    def __call__(self, transactions, value): ...

class OpeningBalance(BalanceBase): ...

class FinalOpeningBalance(BalanceBase): ...

class IntermediateOpeningBalance(BalanceBase): ...

class Statement(Tag):
    scope: Incomplete
    pattern: str
    def __call__(self, transactions, value): ...

class ClosingBalance(BalanceBase): ...

class FinalClosingBalance(ClosingBalance): ...

class IntermediateClosingBalance(ClosingBalance): ...

class AvailableBalance(BalanceBase): ...

class ForwardAvailableBalance(BalanceBase): ...

class TransactionDetails(Tag):
    scope: Incomplete
    pattern: str

class SumEntries(Tag):
    pattern: str
    def __call__(self, transactions, value): ...

class SumDebitEntries(SumEntries):
    status: str

class SumCreditEntries(SumEntries):
    status: str

class Tags(enum.Enum):
    DATE_TIME_INDICATION: Incomplete
    TRANSACTION_REFERENCE_NUMBER: Incomplete
    RELATED_REFERENCE: Incomplete
    ACCOUNT_IDENTIFICATION: Incomplete
    STATEMENT_NUMBER: Incomplete
    OPENING_BALANCE: Incomplete
    INTERMEDIATE_OPENING_BALANCE: Incomplete
    FINAL_OPENING_BALANCE: Incomplete
    STATEMENT: Incomplete
    CLOSING_BALANCE: Incomplete
    INTERMEDIATE_CLOSING_BALANCE: Incomplete
    FINAL_CLOSING_BALANCE: Incomplete
    AVAILABLE_BALANCE: Incomplete
    FORWARD_AVAILABLE_BALANCE: Incomplete
    TRANSACTION_DETAILS: Incomplete
    FLOOR_LIMIT_INDICATOR: Incomplete
    NON_SWIFT: Incomplete
    SUM_ENTRIES: Incomplete
    SUM_DEBIT_ENTRIES: Incomplete
    SUM_CREDIT_ENTRIES: Incomplete

TAG_BY_ID: Incomplete
