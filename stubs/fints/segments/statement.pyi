from .base import FinTS3Segment as FinTS3Segment, ParameterSegment as ParameterSegment
from _typeshed import Incomplete
from fints.fields import (
    CodeField as CodeField,
    DataElementField as DataElementField,
    DataElementGroupField as DataElementGroupField,
)
from fints.formals import (
    Account2 as Account2,
    Account3 as Account3,
    BookedCamtStatements1 as BookedCamtStatements1,
    Confirmation as Confirmation,
    KTI1 as KTI1,
    QueryCreditCardStatements2 as QueryCreditCardStatements2,
    ReportPeriod2 as ReportPeriod2,
    StatementFormat as StatementFormat,
    SupportedMessageTypes as SupportedMessageTypes,
    TransactionsTimeParameter1 as TransactionsTimeParameter1,
)

class HKKAZ5(FinTS3Segment):
    account: Incomplete
    all_accounts: Incomplete
    date_start: Incomplete
    date_end: Incomplete
    max_number_responses: Incomplete
    touchdown_point: Incomplete

class HIKAZ5(FinTS3Segment):
    statement_booked: Incomplete
    statement_pending: Incomplete

class HKKAZ6(FinTS3Segment):
    account: Incomplete
    all_accounts: Incomplete
    date_start: Incomplete
    date_end: Incomplete
    max_number_responses: Incomplete
    touchdown_point: Incomplete

class HIKAZ6(FinTS3Segment):
    statement_booked: Incomplete
    statement_pending: Incomplete

class HKKAZ7(FinTS3Segment):
    account: Incomplete
    all_accounts: Incomplete
    date_start: Incomplete
    date_end: Incomplete
    max_number_responses: Incomplete
    touchdown_point: Incomplete

class HIKAZ7(FinTS3Segment):
    statement_booked: Incomplete
    statement_pending: Incomplete

class DKKKU2(FinTS3Segment):
    account: Incomplete
    credit_card_number: Incomplete
    subaccount: Incomplete
    date_start: Incomplete
    date_end: Incomplete
    max_number_responses: Incomplete
    touchdown_point: Incomplete

class DIKKU2(FinTS3Segment): ...

class DIKKUS2(ParameterSegment):
    parameter: Incomplete

class HICAZS1(ParameterSegment):
    parameter: Incomplete

class HKCAZ1(FinTS3Segment):
    account: Incomplete
    supported_camt_messages: Incomplete
    all_accounts: Incomplete
    date_start: Incomplete
    date_end: Incomplete
    max_number_responses: Incomplete
    touchdown_point: Incomplete

class HICAZ1(FinTS3Segment):
    account: Incomplete
    camt_descriptor: Incomplete
    statement_booked: Incomplete
    statement_pending: Incomplete

class HKKAU1(FinTS3Segment):
    account: Incomplete
    max_number_responses: Incomplete
    touchdown_point: Incomplete

class HKKAU2(FinTS3Segment):
    account: Incomplete
    max_number_responses: Incomplete
    touchdown_point: Incomplete

class HIKAU1(FinTS3Segment):
    statement_number: Incomplete
    confirmation: Incomplete
    collection_possible: Incomplete
    year: Incomplete
    date_created: Incomplete
    time_created: Incomplete
    creation_type: Incomplete

class HIKAU2(FinTS3Segment):
    statement_number: Incomplete
    confirmation: Incomplete
    collection_possible: Incomplete
    year: Incomplete
    date_created: Incomplete
    time_created: Incomplete
    creation_type: Incomplete

class HKEKA3(FinTS3Segment):
    account: Incomplete
    statement_format: Incomplete
    statement_number: Incomplete
    statement_year: Incomplete
    max_number_responses: Incomplete
    touchdown_point: Incomplete

class HKEKA4(FinTS3Segment):
    account: Incomplete
    statement_format: Incomplete
    statement_number: Incomplete
    statement_year: Incomplete
    max_number_responses: Incomplete
    touchdown_point: Incomplete

class HKEKA5(FinTS3Segment):
    account: Incomplete
    statement_format: Incomplete
    statement_number: Incomplete
    statement_year: Incomplete
    max_number_responses: Incomplete
    touchdown_point: Incomplete

class HIEKA3(FinTS3Segment):
    statement_format: Incomplete
    statement_period: Incomplete
    data: Incomplete
    statement_info: Incomplete
    customer_info: Incomplete
    advertising_text: Incomplete
    account_iban: Incomplete
    account_bic: Incomplete
    statement_name_1: Incomplete
    statement_name_2: Incomplete
    statement_name_extra: Incomplete
    confirmation_code: Incomplete

class HIEKA4(FinTS3Segment):
    statement_format: Incomplete
    statement_period: Incomplete
    data: Incomplete
    statement_info: Incomplete
    customer_info: Incomplete
    advertising_text: Incomplete
    account_iban: Incomplete
    account_bic: Incomplete
    statement_name_1: Incomplete
    statement_name_2: Incomplete
    statement_name_extra: Incomplete
    confirmation_code: Incomplete

class HIEKA5(FinTS3Segment):
    statement_format: Incomplete
    statement_period: Incomplete
    date_created: Incomplete
    statement_year: Incomplete
    statement_number: Incomplete
    data: Incomplete
    statement_info: Incomplete
    customer_info: Incomplete
    advertising_text: Incomplete
    account_iban: Incomplete
    account_bic: Incomplete
    statement_name_1: Incomplete
    statement_name_2: Incomplete
    statement_name_extra: Incomplete
    confirmation_code: Incomplete
