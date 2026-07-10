from fints.fields import (
    DataElementField as DataElementField,
    ContainerField as ContainerField,
    DataElementGroupField as DataElementGroupField,
    GenericField as GenericField,
    GenericGroupField as GenericGroupField,
    TextField as TextField,
    AlphanumericField as AlphanumericField,
    DTAUSField as DTAUSField,
    NumericField as NumericField,
    ZeroPaddedNumericField as ZeroPaddedNumericField,
    DigitsField as DigitsField,
    FloatField as FloatField,
    AmountField as AmountField,
    BinaryField as BinaryField,
    IDField as IDField,
    BooleanField as BooleanField,
    CodeFieldMixin as CodeFieldMixin,
    CodeField as CodeField,
    IntCodeField as IntCodeField,
    CountryField as CountryField,
    CurrencyField as CurrencyField,
    DateField as DateField,
    TimeField as TimeField,
    TimestampField as TimestampField,
    PasswordField as PasswordField,
    SegmentSequenceField as SegmentSequenceField,
)
from fints.types import (
    Field as Field,
    TypedField as TypedField,
    ValueList as ValueList,
    SegmentSequence as SegmentSequence,
    ContainerMeta as ContainerMeta,
    Container as Container,
)
from _typeshed import Incomplete
from fints.utils import (
    RepresentableEnum as RepresentableEnum,
    ShortReprMixin as ShortReprMixin,
    doc_enum as doc_enum,
)
from typing import override

CUSTOMER_ID_ANONYMOUS: str

class DataElementGroup(Container): ...

class SegmentHeader(ShortReprMixin, DataElementGroup):
    type: Incomplete
    number: Incomplete
    version: Incomplete
    reference: Incomplete

class ReferenceMessage(DataElementGroup):
    dialog_id: Incomplete
    message_number: Incomplete

class SecurityMethod(RepresentableEnum):
    DDV = "DDV"
    RAH = "RAH"
    RDH = "RDH"
    PIN = "PIN"

class SecurityProfile(DataElementGroup):
    security_method: Incomplete
    security_method_version: Incomplete

class IdentifiedRole(RepresentableEnum):
    MS = "1"
    MR = "2"

class SecurityIdentificationDetails(DataElementGroup):
    identified_role: Incomplete
    cid: Incomplete
    identifier: Incomplete

class DateTimeType(RepresentableEnum):
    STS = "1"
    CRT = "6"

class SecurityDateTime(DataElementGroup):
    date_time_type: Incomplete
    date: Incomplete
    time: Incomplete

class UsageEncryption(RepresentableEnum):
    OSY = "2"

class OperationMode(RepresentableEnum):
    CBC = "2"
    ISO_9796_1 = "16"
    ISO_9796_2_RANDOM = "17"
    PKCS1V15 = "18"
    PSS = "19"
    ZZZ = "999"

class EncryptionAlgorithmCoded(RepresentableEnum):
    TWOKEY3DES = "13"
    AES256 = "14"

class AlgorithmParameterName(RepresentableEnum):
    KYE = "5"
    KYP = "6"

class AlgorithmParameterIVName(RepresentableEnum):
    IVC = "1"

class EncryptionAlgorithm(DataElementGroup):
    usage_encryption: Incomplete
    operation_mode: Incomplete
    encryption_algorithm: Incomplete
    algorithm_parameter_value: Incomplete
    algorithm_parameter_name: Incomplete
    algorithm_parameter_iv_name: Incomplete
    algorithm_parameter_iv_value: Incomplete

class HashAlgorithm(DataElementGroup):
    usage_hash: Incomplete
    hash_algorithm: Incomplete
    algorithm_parameter_name: Incomplete
    algorithm_parameter_value: Incomplete

class SignatureAlgorithm(DataElementGroup):
    usage_signature: Incomplete
    signature_algorithm: Incomplete
    operation_mode: Incomplete

class BankIdentifier(DataElementGroup):
    COUNTRY_ALPHA_TO_NUMERIC: Incomplete
    COUNTRY_NUMERIC_TO_ALPHA: Incomplete
    country_identifier: Incomplete
    bank_code: Incomplete
    @override
    def __eq__(self, other): ...

class KeyType(RepresentableEnum):
    D = "D"
    S = "S"
    V = "V"

class KeyName(DataElementGroup):
    bank_identifier: Incomplete
    user_id: Incomplete
    key_type: Incomplete
    key_number: Incomplete
    key_version: Incomplete

class Certificate(DataElementGroup):
    certificate_type: Incomplete
    certificate_content: Incomplete

class UserDefinedSignature(DataElementGroup):
    pin: Incomplete
    tan: Incomplete

class Response(DataElementGroup):
    code: Incomplete
    reference_element: Incomplete
    text: Incomplete
    parameters: Incomplete

class Amount1(DataElementGroup):
    amount: Incomplete
    currency: Incomplete

class AccountInformation(DataElementGroup):
    account_number: Incomplete
    subaccount_number: Incomplete
    bank_identifier: Incomplete

class AccountLimit(DataElementGroup):
    limit_type: Incomplete
    limit_amount: Incomplete
    limit_days: Incomplete

class AllowedTransaction(DataElementGroup):
    transaction: Incomplete
    required_signatures: Incomplete
    limit_type: Incomplete
    limit_amount: Incomplete
    limit_days: Incomplete

class TANTimeDialogAssociation(RepresentableEnum):
    NOT_ALLOWED = "1"
    ALLOWED = "2"
    BOTH = "3"
    NOT_APPLICABLE = "4"

class AllowedFormat(RepresentableEnum):
    NUMERIC = "1"
    ALPHANUMERIC = "2"

class TANListNumberRequired(RepresentableEnum):
    NO = "0"
    YES = "2"

class InitializationMode(RepresentableEnum):
    CLEARTEXT_PIN_NO_TAN = "00"
    ENCRYPTED_PIN_NO_TAN = "01"
    MASK_02 = "02"

class DescriptionRequired(RepresentableEnum):
    MUST_NOT = "0"
    MAY = "1"
    MUST = "2"

class SMSChargeAccountRequired(RepresentableEnum):
    MUST_NOT = "0"
    MAY = "1"
    MUST = "2"

class PrincipalAccountRequired(RepresentableEnum):
    MUST_NOT = "0"
    MUST = "2"

class TaskHashAlgorithm(RepresentableEnum):
    NONE = "0"
    RIPEMD_160 = "1"
    SHA_1 = "2"

class TwoStepParametersCommon(DataElementGroup):
    @property
    def VERSION(self): ...
    security_function: Incomplete
    tan_process: Incomplete
    tech_id: Incomplete

class TwoStepParameters1(TwoStepParametersCommon):
    name: Incomplete
    max_length_input: Incomplete
    allowed_format: Incomplete
    text_return_value: Incomplete
    max_length_return_value: Incomplete
    number_of_supported_lists: Incomplete
    multiple_tans_allowed: Incomplete
    tan_time_delayed_allowed: Incomplete

class TwoStepParameters2(TwoStepParametersCommon):
    name: Incomplete
    max_length_input: Incomplete
    allowed_format: Incomplete
    text_return_value: Incomplete
    max_length_return_value: Incomplete
    number_of_supported_lists: Incomplete
    multiple_tans_allowed: Incomplete
    tan_time_dialog_association: Incomplete
    tan_list_number_required: Incomplete
    cancel_allowed: Incomplete
    challenge_class_required: Incomplete
    challenge_value_required: Incomplete

class TwoStepParameters3(TwoStepParametersCommon):
    name: Incomplete
    max_length_input: Incomplete
    allowed_format: Incomplete
    text_return_value: Incomplete
    max_length_return_value: Incomplete
    number_of_supported_lists: Incomplete
    multiple_tans_allowed: Incomplete
    tan_time_dialog_association: Incomplete
    tan_list_number_required: Incomplete
    cancel_allowed: Incomplete
    challenge_class_required: Incomplete
    challenge_value_required: Incomplete
    initialization_mode: Incomplete
    description_required: Incomplete
    supported_media_number: Incomplete

class TwoStepParameters4(TwoStepParametersCommon):
    zka_id: Incomplete
    zka_version: Incomplete
    name: Incomplete
    max_length_input: Incomplete
    allowed_format: Incomplete
    text_return_value: Incomplete
    max_length_return_value: Incomplete
    number_of_supported_lists: Incomplete
    multiple_tans_allowed: Incomplete
    tan_time_dialog_association: Incomplete
    tan_list_number_required: Incomplete
    cancel_allowed: Incomplete
    sms_charge_account_required: Incomplete
    challenge_class_required: Incomplete
    challenge_value_required: Incomplete
    challenge_structured: Incomplete
    initialization_mode: Incomplete
    description_required: Incomplete
    supported_media_number: Incomplete

class TwoStepParameters5(TwoStepParametersCommon):
    zka_id: Incomplete
    zka_version: Incomplete
    name: Incomplete
    max_length_input: Incomplete
    allowed_format: Incomplete
    text_return_value: Incomplete
    max_length_return_value: Incomplete
    number_of_supported_lists: Incomplete
    multiple_tans_allowed: Incomplete
    tan_time_dialog_association: Incomplete
    tan_list_number_required: Incomplete
    cancel_allowed: Incomplete
    sms_charge_account_required: Incomplete
    principal_account_required: Incomplete
    challenge_class_required: Incomplete
    challenge_structured: Incomplete
    initialization_mode: Incomplete
    description_required: Incomplete
    supported_media_number: Incomplete

class TwoStepParameters6(TwoStepParametersCommon):
    zka_id: Incomplete
    zka_version: Incomplete
    name: Incomplete
    max_length_input: Incomplete
    allowed_format: Incomplete
    text_return_value: Incomplete
    max_length_return_value: Incomplete
    multiple_tans_allowed: Incomplete
    tan_time_dialog_association: Incomplete
    cancel_allowed: Incomplete
    sms_charge_account_required: Incomplete
    principal_account_required: Incomplete
    challenge_class_required: Incomplete
    challenge_structured: Incomplete
    initialization_mode: Incomplete
    description_required: Incomplete
    response_hhd_uc_required: Incomplete
    supported_media_number: Incomplete

class TwoStepParameters7(TwoStepParametersCommon):
    zka_id: Incomplete
    zka_version: Incomplete
    name: Incomplete
    max_length_input: Incomplete
    allowed_format: Incomplete
    text_return_value: Incomplete
    max_length_return_value: Incomplete
    multiple_tans_allowed: Incomplete
    tan_time_dialog_association: Incomplete
    cancel_allowed: Incomplete
    sms_charge_account_required: Incomplete
    principal_account_required: Incomplete
    challenge_class_required: Incomplete
    challenge_structured: Incomplete
    initialization_mode: Incomplete
    description_required: Incomplete
    response_hhd_uc_required: Incomplete
    supported_media_number: Incomplete
    decoupled_max_poll_number: Incomplete
    wait_before_first_poll: Incomplete
    wait_before_next_poll: Incomplete
    manual_confirmation_allowed: Incomplete
    automated_polling_allowed: Incomplete

class ParameterTwostepCommon(DataElementGroup):
    onestep_method_allowed: Incomplete
    multiple_tasks_allowed: Incomplete
    task_hash_algorithm: Incomplete

class ParameterTwostepTAN1(ParameterTwostepCommon):
    security_profile_bank_signature: Incomplete
    twostep_parameters: Incomplete

class ParameterTwostepTAN2(ParameterTwostepCommon):
    twostep_parameters: Incomplete

class ParameterTwostepTAN3(ParameterTwostepCommon):
    twostep_parameters: Incomplete

class ParameterTwostepTAN4(ParameterTwostepCommon):
    twostep_parameters: Incomplete

class ParameterTwostepTAN5(ParameterTwostepCommon):
    twostep_parameters: Incomplete

class ParameterTwostepTAN6(ParameterTwostepCommon):
    twostep_parameters: Incomplete

class ParameterTwostepTAN7(ParameterTwostepCommon):
    twostep_parameters: Incomplete

class TransactionTanRequired(DataElementGroup):
    transaction: Incomplete
    tan_required: Incomplete

class ParameterPinTan(DataElementGroup):
    min_pin_length: Incomplete
    max_pin_length: Incomplete
    max_tan_length: Incomplete
    user_id_field_text: Incomplete
    customer_id_field_text: Incomplete
    transaction_tans_required: Incomplete

class Language2(RepresentableEnum):
    DEFAULT = "0"
    DE = "1"
    EN = "2"
    FR = "3"

class SupportedLanguages2(DataElementGroup):
    languages: Incomplete

class SupportedHBCIVersions2(DataElementGroup):
    versions: Incomplete

class KTZ1(DataElementGroup):
    is_sepa: Incomplete
    iban: Incomplete
    bic: Incomplete
    account_number: Incomplete
    subaccount_number: Incomplete
    bank_identifier: Incomplete
    def as_sepa_account(self): ...
    @classmethod
    def from_sepa_account(cls, acc): ...

class KTI1(DataElementGroup):
    iban: Incomplete
    bic: Incomplete
    account_number: Incomplete
    subaccount_number: Incomplete
    bank_identifier: Incomplete
    @classmethod
    def from_sepa_account(cls, acc): ...

class Account2(DataElementGroup):
    account_number: Incomplete
    subaccount_number: Incomplete
    country_identifier: Incomplete
    bank_code: Incomplete
    @classmethod
    def from_sepa_account(cls, acc): ...

class Account3(DataElementGroup):
    account_number: Incomplete
    subaccount_number: Incomplete
    bank_identifier: Incomplete
    @classmethod
    def from_sepa_account(cls, acc): ...

class SecurityRole(RepresentableEnum):
    ISS = "1"
    CON = "3"
    WIT = "4"

class CompressionFunction(RepresentableEnum):
    NULL = "0"
    LZW = "1"
    COM = "2"
    LZSS = "3"
    LZHuf = "4"
    ZIP = "5"
    GZIP = "6"
    BZIP2 = "7"
    ZZZ = "999"

class SecurityApplicationArea(RepresentableEnum):
    SHM = "1"
    SHT = "2"

class SecurityClass(RepresentableEnum):
    NONE = 0
    AUTH = 1
    AUTH_ADV = 2
    NON_REPUD = 3
    NON_REPUD_QUAL = 4

class UPDUsage(RepresentableEnum):
    UPD_CONCLUSIVE = "0"
    UPD_INCONCLUSIVE = "1"

class SystemIDStatus(RepresentableEnum):
    ID_UNNECESSARY = "0"
    ID_NECESSARY = "1"

class SynchronizationMode(RepresentableEnum):
    NEW_SYSTEM_ID = "0"
    LAST_MESSAGE = "1"
    SIGNATURE_ID = "2"

class CreditDebit2(RepresentableEnum):
    CREDIT = "C"
    DEBIT = "D"

class Balance1(DataElementGroup):
    credit_debit: Incomplete
    amount: Incomplete
    currency: Incomplete
    date: Incomplete
    time: Incomplete
    def as_mt940_Balance(self): ...

class Balance2(DataElementGroup):
    credit_debit: Incomplete
    amount: Incomplete
    date: Incomplete
    time: Incomplete
    def as_mt940_Balance(self): ...

class Timestamp1(DataElementGroup):
    date: Incomplete
    time: Incomplete

class TANMediaType2(RepresentableEnum):
    ALL = "0"
    ACTIVE = "1"
    AVAILABLE = "2"

class TANMediaClass3(RepresentableEnum):
    ALL = "A"
    LIST = "L"
    GENERATOR = "G"
    MOBILE = "M"
    SECODER = "S"

class TANMediaClass4(RepresentableEnum):
    ALL = "A"
    LIST = "L"
    GENERATOR = "G"
    MOBILE = "M"
    SECODER = "S"
    BILATERAL = "B"

class TANMediumStatus(RepresentableEnum):
    ACTIVE = "1"
    AVAILABLE = "2"
    ACTIVE_SUCCESSOR = "3"
    AVAILABLE_SUCCESSOR = "4"

class TANMedia4(DataElementGroup):
    tan_medium_class: Incomplete
    status: Incomplete
    card_number: Incomplete
    card_sequence: Incomplete
    card_type: Incomplete
    account: Incomplete
    valid_from: Incomplete
    valid_until: Incomplete
    tan_list_number: Incomplete
    tan_medium_name: Incomplete
    mobile_number_masked: Incomplete
    mobile_number: Incomplete
    sms_charge_account: Incomplete
    number_free_tans: Incomplete
    last_use: Incomplete
    active_since: Incomplete

class TANMedia5(DataElementGroup):
    tan_medium_class: Incomplete
    status: Incomplete
    security_function: Incomplete
    card_number: Incomplete
    card_sequence: Incomplete
    card_type: Incomplete
    account: Incomplete
    valid_from: Incomplete
    valid_until: Incomplete
    tan_list_number: Incomplete
    tan_medium_name: Incomplete
    mobile_number_masked: Incomplete
    mobile_number: Incomplete
    sms_charge_account: Incomplete
    number_free_tans: Incomplete
    last_use: Incomplete
    active_since: Incomplete

class TANUsageOption(RepresentableEnum):
    ALL_ACTIVE = "0"
    EXACTLY_ONE = "1"
    MOBILE_AND_GENERATOR = "2"

class ParameterChallengeClass(DataElementGroup):
    parameters: Incomplete

class ResponseHHDUC(DataElementGroup):
    atc: Incomplete
    ac: Incomplete
    ef_id_data: Incomplete
    cvr: Incomplete
    version_info_chiptan: Incomplete

class ChallengeValidUntil(DataElementGroup):
    date: Incomplete
    time: Incomplete

class BatchTransferParameter1(DataElementGroup):
    max_transfer_count: Incomplete
    sum_amount_required: Incomplete
    single_booking_allowed: Incomplete

class ServiceType2(RepresentableEnum):
    T_ONLINE = 1
    TCP_IP = 2
    HTTPS = 3

class CommunicationParameter2(DataElementGroup):
    service_type: Incomplete
    address: Incomplete
    address_adjunct: Incomplete
    filter_function: Incomplete
    filter_function_version: Incomplete

class ScheduledDebitParameter1(DataElementGroup):
    min_advance_notice_FNAL_RCUR: Incomplete
    max_advance_notice_FNAL_RCUR: Incomplete
    min_advance_notice_FRST_OOFF: Incomplete
    max_advance_notice_FRST_OOFF: Incomplete

class ScheduledDebitParameter2(DataElementGroup):
    min_advance_notice: Incomplete
    max_advance_notice: Incomplete
    allowed_purpose_codes: Incomplete
    supported_sepa_formats: Incomplete

class ScheduledBatchDebitParameter1(DataElementGroup):
    min_advance_notice_FNAL_RCUR: Incomplete
    max_advance_notice_FNAL_RCUR: Incomplete
    min_advance_notice_FRST_OOFF: Incomplete
    max_advance_notice_FRST_OOFF: Incomplete
    max_debit_count: Incomplete
    sum_amount_required: Incomplete
    single_booking_allowed: Incomplete

class TransactionsTimeParameter1(DataElementGroup):
    storage_duration: Incomplete
    entry_number_entries_allowed: Incomplete
    all_accounts_allowed: Incomplete
    supported_camt_formats: Incomplete

class ScheduledBatchDebitParameter2(DataElementGroup):
    min_advance_notice: Incomplete
    max_advance_notice: Incomplete
    max_debit_count: Incomplete
    sum_amount_required: Incomplete
    single_booking_allowed: Incomplete
    allowed_purpose_codes: Incomplete
    supported_sepa_formats: Incomplete

class ScheduledCOR1DebitParameter1(DataElementGroup):
    min_advance_notice_FNAL_RCUR: Incomplete
    max_advance_notice_FNAL_RCUR: Incomplete
    min_advance_notice_FRST_OOFF: Incomplete
    max_advance_notice_FRST_OOFF: Incomplete
    allowed_purpose_codes: Incomplete
    supported_sepa_formats: Incomplete

class ScheduledCOR1BatchDebitParameter1(DataElementGroup):
    max_debit_count: Incomplete
    sum_amount_required: Incomplete
    single_booking_allowed: Incomplete
    min_advance_notice_FNAL_RCUR: Incomplete
    max_advance_notice_FNAL_RCUR: Incomplete
    min_advance_notice_FRST_OOFF: Incomplete
    max_advance_notice_FRST_OOFF: Incomplete
    allowed_purpose_codes: Incomplete
    supported_sepa_formats: Incomplete

class SupportedSEPAPainMessages1(DataElementGroup):
    sepa_descriptors: Incomplete

class QueryScheduledDebitParameter1(DataElementGroup):
    date_range_allowed: Incomplete
    max_number_responses_allowed: Incomplete

class QueryScheduledDebitParameter2(DataElementGroup):
    max_number_responses_allowed: Incomplete
    date_range_allowed: Incomplete
    supported_sepa_formats: Incomplete

class QueryScheduledBatchDebitParameter1(DataElementGroup):
    max_number_responses_allowed: Incomplete
    date_range_allowed: Incomplete

class QueryCreditCardStatements2(DataElementGroup):
    cutoff_days: Incomplete
    max_number_responses_allowed: Incomplete
    date_range_allowed: Incomplete

class SEPACCode1(RepresentableEnum):
    REVERSAL = "1"
    REVOCATION = "2"
    DELETION = "3"

class StatusSEPATask1(RepresentableEnum):
    PENDING = "1"
    DECLINED = "2"
    IN_PROGRESS = "3"
    PROCESSED = "4"
    REVOKED = "5"

class GetSEPAAccountParameter1(DataElementGroup):
    single_account_query_allowed: Incomplete
    national_account_allowed: Incomplete
    structured_purpose_allowed: Incomplete
    supported_sepa_formats: Incomplete

class GetSEPAAccountParameter3(DataElementGroup):
    single_account_query_allowed: Incomplete
    national_account_allowed: Incomplete
    structured_purpose_allowed: Incomplete
    max_number_responses_allowed: Incomplete
    cutoff_days: Incomplete
    supported_sepa_formats: Incomplete

class SupportedMessageTypes(DataElementGroup):
    expected_type: Incomplete

class BookedCamtStatements1(DataElementGroup):
    camt_statements: Incomplete

class StatementFormat(RepresentableEnum):
    MT_940 = "1"
    ISO_8583 = "2"
    PDF = "3"

class Confirmation(RepresentableEnum):
    NOT_REQUIRED = "0"
    CONFIRMED = "1"
    AWAITING_CONFIRMATION = "2"

class ReportPeriod2(DataElementGroup):
    start_date: Incomplete
    end_date: Incomplete
