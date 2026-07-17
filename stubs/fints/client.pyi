import datetime
import types
from abc import ABCMeta, abstractmethod
from collections.abc import Generator
from contextlib import contextmanager
from decimal import Decimal
from enum import Enum
from typing import override

from _typeshed import Incomplete
from mt940.models import Transaction as MT940Transaction

from . import version as version
from .camt_parser import camt053_to_dict as camt053_to_dict
from .connection import FinTSHTTPSConnection as FinTSHTTPSConnection
from .dialog import FinTSDialog as FinTSDialog
from .formals import (
    CUSTOMER_ID_ANONYMOUS as CUSTOMER_ID_ANONYMOUS,
    KTI1 as KTI1,
    BankIdentifier as BankIdentifier,
    DescriptionRequired as DescriptionRequired,
    StatementFormat as StatementFormat,
    SupportedMessageTypes as SupportedMessageTypes,
    SynchronizationMode as SynchronizationMode,
    TANMediaClass4 as TANMediaClass4,
    TANMediaType2 as TANMediaType2,
    TANUsageOption as TANUsageOption,
    TwoStepParameters1 as TwoStepParameters1,
    TwoStepParameters2 as TwoStepParameters2,
    TwoStepParameters3 as TwoStepParameters3,
    TwoStepParameters4 as TwoStepParameters4,
    TwoStepParameters5 as TwoStepParameters5,
    TwoStepParameters6 as TwoStepParameters6,
    TwoStepParameters7 as TwoStepParameters7,
)
from .message import FinTSInstituteMessage as FinTSInstituteMessage
from .models import SEPAAccount as SEPAAccount
from .models import Transaction as Transaction
from .parser import FinTS3Serializer as FinTS3Serializer
from .security import (
    PinTanDummyEncryptionMechanism as PinTanDummyEncryptionMechanism,
)
from .security import (
    PinTanOneStepAuthenticationMechanism as PinTanOneStepAuthenticationMechanism,
)
from .security import (
    PinTanTwoStepAuthenticationMechanism as PinTanTwoStepAuthenticationMechanism,
)
from .segments.accounts import HISPA1 as HISPA1
from .segments.accounts import HKSPA1 as HKSPA1
from .segments.auth import (
    HIPINS1 as HIPINS1,
)
from .segments.auth import (
    HIVPP1 as HIVPP1,
)
from .segments.auth import (
    HIVPPS1 as HIVPPS1,
)
from .segments.auth import (
    HKTAB4 as HKTAB4,
)
from .segments.auth import (
    HKTAB5 as HKTAB5,
)
from .segments.auth import (
    HKTAN2 as HKTAN2,
)
from .segments.auth import (
    HKTAN3 as HKTAN3,
)
from .segments.auth import (
    HKTAN5 as HKTAN5,
)
from .segments.auth import (
    HKTAN6 as HKTAN6,
)
from .segments.auth import (
    HKTAN7 as HKTAN7,
)
from .segments.auth import (
    HKVPA1 as HKVPA1,
)
from .segments.auth import (
    PSRD1 as PSRD1,
)
from .segments.bank import HIBPA3 as HIBPA3
from .segments.bank import HIUPA4 as HIUPA4
from .segments.bank import HKKOM4 as HKKOM4
from .segments.debit import (
    HKDBS1 as HKDBS1,
)
from .segments.debit import (
    HKDBS2 as HKDBS2,
)
from .segments.debit import (
    HKDMB1 as HKDMB1,
)
from .segments.debit import (
    HKDMC1 as HKDMC1,
)
from .segments.debit import (
    HKDME1 as HKDME1,
)
from .segments.debit import (
    HKDME2 as HKDME2,
)
from .segments.debit import (
    HKDSC1 as HKDSC1,
)
from .segments.debit import (
    HKDSE1 as HKDSE1,
)
from .segments.debit import (
    HKDSE2 as HKDSE2,
)
from .segments.debit import (
    DebitResponseBase as DebitResponseBase,
)
from .segments.depot import HKWPD5 as HKWPD5
from .segments.depot import HKWPD6 as HKWPD6
from .segments.dialog import HIRMG2 as HIRMG2
from .segments.dialog import HIRMS2 as HIRMS2
from .segments.dialog import HISYN4 as HISYN4
from .segments.dialog import HKSYN3 as HKSYN3
from .segments.journal import HKPRO3 as HKPRO3
from .segments.journal import HKPRO4 as HKPRO4
from .segments.saldo import HKSAL5 as HKSAL5
from .segments.saldo import HKSAL6 as HKSAL6
from .segments.saldo import HKSAL7 as HKSAL7
from .segments.statement import (
    DKKKU2 as DKKKU2,
)
from .segments.statement import (
    HKCAZ1 as HKCAZ1,
)
from .segments.statement import (
    HKEKA3 as HKEKA3,
)
from .segments.statement import (
    HKEKA4 as HKEKA4,
)
from .segments.statement import (
    HKEKA5 as HKEKA5,
)
from .segments.statement import (
    HKKAU1 as HKKAU1,
)
from .segments.statement import (
    HKKAU2 as HKKAU2,
)
from .segments.statement import (
    HKKAZ5 as HKKAZ5,
)
from .segments.statement import (
    HKKAZ6 as HKKAZ6,
)
from .segments.statement import (
    HKKAZ7 as HKKAZ7,
)
from .segments.transfer import (
    HKCCM1 as HKCCM1,
)
from .segments.transfer import (
    HKCCS1 as HKCCS1,
)
from .segments.transfer import (
    HKIPM1 as HKIPM1,
)
from .segments.transfer import (
    HKIPZ1 as HKIPZ1,
)
from .types import SegmentSequence as SegmentSequence
from .utils import (
    MT535_Miniparser as MT535_Miniparser,
)
from .utils import (
    Password as Password,
)
from .utils import (
    SubclassesMixin as SubclassesMixin,
)
from .utils import (
    compress_datablob as compress_datablob,
)
from .utils import (
    decompress_datablob as decompress_datablob,
)
from .utils import (
    mt940_to_array as mt940_to_array,
)

logger: Incomplete
SYSTEM_ID_UNASSIGNED: str
DATA_BLOB_MAGIC: bytes
DATA_BLOB_MAGIC_RETRY: bytes
ING_BANK_IDENTIFIER: Incomplete

class FinTSOperations(Enum):
    GET_BALANCE = ("HKSAL",)
    GET_TRANSACTIONS = ("HKKAZ",)
    GET_TRANSACTIONS_XML = ("HKCAZ",)
    GET_CREDIT_CARD_TRANSACTIONS = ("DKKKU",)
    GET_STATEMENT = ("HKEKA",)
    GET_STATEMENT_PDF = ("HKEKP",)
    GET_HOLDINGS = ("HKWPD",)
    GET_SEPA_ACCOUNTS = ("HKSPA",)
    GET_SCHEDULED_DEBITS_SINGLE = ("HKDBS",)
    GET_SCHEDULED_DEBITS_MULTIPLE = ("HKDMB",)
    GET_STATUS_PROTOCOL = ("HKPRO",)
    SEPA_TRANSFER_SINGLE = ("HKCCS",)
    SEPA_TRANSFER_MULTIPLE = ("HKCCM",)
    SEPA_DEBIT_SINGLE = ("HKDSE",)
    SEPA_DEBIT_MULTIPLE = ("HKDME",)
    SEPA_DEBIT_SINGLE_COR1 = ("HKDSC",)
    SEPA_DEBIT_MULTIPLE_COR1 = ("HKDMC",)
    SEPA_STANDING_DEBIT_SINGLE_CREATE = ("HKDDE",)
    GET_SEPA_STANDING_DEBITS_SINGLE = ("HKDDB",)
    SEPA_STANDING_DEBIT_SINGLE_DELETE = ("HKDDL",)

class NeedRetryResponse(SubclassesMixin, metaclass=ABCMeta):
    @abstractmethod
    def get_data(self) -> bytes: ...
    @classmethod
    def from_data(cls, blob) -> NeedRetryResponse: ...

class ResponseStatus(Enum):
    UNKNOWN = 0
    SUCCESS = 1
    WARNING = 2
    ERROR = 3

class TransactionResponse:
    status = ResponseStatus
    responses = list
    data = dict
    def __init__(self, response_message) -> None: ...
    def set_status_if_higher(self, status) -> None: ...

class FinTSClientMode(Enum):
    OFFLINE = "offline"
    INTERACTIVE = "interactive"

class FinTS3Client:
    accounts: Incomplete
    bank_identifier: Incomplete
    system_id: Incomplete
    user_id: Incomplete
    customer_id: Incomplete
    bpd_version: int
    bpa: Incomplete
    bpd: Incomplete
    upd_version: int
    upa: Incomplete
    upd: Incomplete
    product_name: Incomplete
    product_version: Incomplete
    response_callbacks: Incomplete
    mode: Incomplete
    init_tan_response: Incomplete
    def __init__(
        self,
        bank_identifier,
        user_id,
        customer_id: Incomplete | None = None,
        from_data: bytes = None,
        system_id: Incomplete | None = None,
        product_id: Incomplete | None = None,
        product_version=...,
        mode=...,
    ) -> None: ...
    def process_response_message(
        self, dialog, message: FinTSInstituteMessage, internal_send: bool = True
    ): ...
    def __enter__(self) -> None: ...
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> None: ...
    def deconstruct(self, including_private: bool = False) -> bytes: ...
    def set_data(self, blob: bytes): ...
    def get_information(self): ...
    def get_sepa_accounts(self) -> list[SEPAAccount]: ...
    def get_transactions(
        self,
        account: SEPAAccount,
        start_date: datetime.date = None,
        end_date: datetime.date = None,
        include_pending: bool = False,
    ) -> list[MT940Transaction] | list[Transaction]: ...
    def get_transactions_xml(
        self,
        account: SEPAAccount,
        start_date: datetime.date = None,
        end_date: datetime.date = None,
        supported_camt_messages: Incomplete | None = None,
    ) -> list: ...
    def get_credit_card_transactions(
        self,
        account: SEPAAccount,
        credit_card_number: str,
        start_date: datetime.date = None,
        end_date: datetime.date = None,
    ): ...
    def get_balance(self, account: SEPAAccount): ...
    def get_holdings(self, account: SEPAAccount): ...
    def get_scheduled_debits(self, account: SEPAAccount, multiple: bool = False): ...
    def get_status_protocol(self): ...
    def get_communication_endpoints(self): ...
    def get_statements(self, account: SEPAAccount): ...
    def get_statement(
        self, account: SEPAAccount, number: int, year: int, format: StatementFormat = None
    ): ...
    def simple_sepa_transfer(
        self,
        account: SEPAAccount,
        iban: str,
        bic: str,
        recipient_name: str,
        amount: Decimal,
        account_name: str,
        reason: str,
        instant_payment: bool = False,
        endtoend_id: str = "NOTPROVIDED",
    ): ...
    def sepa_transfer(
        self,
        account: SEPAAccount,
        pain_message: str,
        multiple: bool = False,
        control_sum: Incomplete | None = None,
        currency: str = "EUR",
        book_as_single: bool = False,
        pain_descriptor: str = "urn:iso:std:iso:20022:tech:xsd:pain.001.001.03",
        instant_payment: bool = False,
    ): ...
    def sepa_debit(
        self,
        account: SEPAAccount,
        pain_message: str,
        multiple: bool = False,
        cor1: bool = False,
        control_sum: Incomplete | None = None,
        currency: str = "EUR",
        book_as_single: bool = False,
        pain_descriptor: str = "urn:iso:std:iso:20022:tech:xsd:pain.008.003.01",
    ): ...
    def add_response_callback(self, cb) -> None: ...
    def remove_response_callback(self, cb) -> None: ...
    def set_product(self, product_name, product_version) -> None: ...
    def pause_dialog(self) -> bytes: ...
    @contextmanager
    def resume_dialog(self, dialog_data) -> Generator[FinTS3Client, None, None]: ...

class NeedVOPResponse(NeedRetryResponse):
    vop_result: Incomplete
    command_seg: Incomplete
    resume_method: Incomplete
    def __init__(
        self, vop_result, command_seg, resume_method: Incomplete | None = None
    ) -> None: ...
    @override
    def get_data(self) -> bytes: ...

class NeedTANResponse(NeedRetryResponse):
    challenge_raw: Incomplete
    challenge: Incomplete
    challenge_html: Incomplete
    challenge_hhduc: Incomplete
    challenge_matrix: Incomplete
    decoupled: Incomplete
    vop_result: Incomplete
    command_seg: Incomplete
    tan_request: Incomplete
    tan_request_structured: Incomplete
    resume_method: Incomplete
    def __init__(
        self,
        command_seg,
        tan_request,
        resume_method: Incomplete | None = None,
        tan_request_structured: bool = False,
        decoupled: bool = False,
        vop_result: Incomplete | None = None,
    ) -> None: ...
    @override
    def get_data(self) -> bytes: ...

IMPLEMENTED_HKTAN_VERSIONS: Incomplete

class FinTS3PinTanClient(FinTS3Client):
    pin: Incomplete
    connection: Incomplete
    allowed_security_functions: Incomplete
    selected_security_function: Incomplete
    selected_tan_medium: Incomplete
    def __init__(
        self,
        bank_identifier,
        user_id,
        pin,
        server,
        customer_id: Incomplete | None = None,
        tan_medium: Incomplete | None = None,
        *args,
        **kwargs,
    ) -> None: ...
    def fetch_tan_mechanisms(self): ...
    def is_tan_media_required(self): ...
    def is_challenge_structured(self): ...
    def approve_vop_response(self, challenge: NeedVOPResponse): ...
    def send_tan(self, challenge: NeedTANResponse, tan: str): ...
    def get_tan_mechanisms(self) -> dict[str, TwoStepParameters1 | TwoStepParameters2 | TwoStepParameters3 | TwoStepParameters4 | TwoStepParameters5 | TwoStepParameters6 | TwoStepParameters7]: ...
    def get_current_tan_mechanism(self): ...
    def set_tan_mechanism(self, security_function) -> None: ...
    def set_tan_medium(self, tan_medium) -> None: ...
    def get_tan_media(self, media_type=..., media_class=...): ...
    @override
    def get_information(self): ...
