from .base import FinTS3Segment as FinTS3Segment
from _typeshed import Incomplete
from fints.fields import (
    CodeField as CodeField,
    DataElementField as DataElementField,
    DataElementGroupField as DataElementGroupField,
)
from fints.formals import (
    AccountInformation as AccountInformation,
    AccountLimit as AccountLimit,
    AllowedTransaction as AllowedTransaction,
    BankIdentifier as BankIdentifier,
    CommunicationParameter2 as CommunicationParameter2,
    Language2 as Language2,
    SupportedHBCIVersions2 as SupportedHBCIVersions2,
    SupportedLanguages2 as SupportedLanguages2,
    UPDUsage as UPDUsage,
)

class HIBPA3(FinTS3Segment):
    bpd_version: Incomplete
    bank_identifier: Incomplete
    bank_name: Incomplete
    number_tasks: Incomplete
    supported_languages: Incomplete
    supported_hbci_version: Incomplete
    max_message_length: Incomplete
    min_timeout: Incomplete
    max_timeout: Incomplete

class HIUPA4(FinTS3Segment):
    user_identifier: Incomplete
    upd_version: Incomplete
    upd_usage: Incomplete
    username: Incomplete
    extension: Incomplete

class HIUPD6(FinTS3Segment):
    account_information: Incomplete
    iban: Incomplete
    customer_id: Incomplete
    account_type: Incomplete
    account_currency: Incomplete
    name_account_owner_1: Incomplete
    name_account_owner_2: Incomplete
    account_product_name: Incomplete
    account_limit: Incomplete
    allowed_transactions: Incomplete
    extension: Incomplete

class HKKOM4(FinTS3Segment):
    start_bank_identifier: Incomplete
    end_bank_identifier: Incomplete
    max_number_responses: Incomplete
    touchdown_point: Incomplete

class HIKOM4(FinTS3Segment):
    bank_identifier: Incomplete
    default_language: Incomplete
    communication_parameters: Incomplete
