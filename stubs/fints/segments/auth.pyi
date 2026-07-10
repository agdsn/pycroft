from .base import FinTS3Segment as FinTS3Segment, ParameterSegment as ParameterSegment
from _typeshed import Incomplete
from fints.fields import (
    CodeField as CodeField,
    DataElementField as DataElementField,
    DataElementGroupField as DataElementGroupField,
)
from fints.formals import (
    BankIdentifier as BankIdentifier,
    ChallengeValidUntil as ChallengeValidUntil,
    DataElementGroup as DataElementGroup,
    KTI1 as KTI1,
    Language2 as Language2,
    ParameterChallengeClass as ParameterChallengeClass,
    ParameterPinTan as ParameterPinTan,
    ParameterTwostepTAN1 as ParameterTwostepTAN1,
    ParameterTwostepTAN2 as ParameterTwostepTAN2,
    ParameterTwostepTAN3 as ParameterTwostepTAN3,
    ParameterTwostepTAN4 as ParameterTwostepTAN4,
    ParameterTwostepTAN5 as ParameterTwostepTAN5,
    ParameterTwostepTAN6 as ParameterTwostepTAN6,
    ParameterTwostepTAN7 as ParameterTwostepTAN7,
    ResponseHHDUC as ResponseHHDUC,
    SystemIDStatus as SystemIDStatus,
    TANMedia4 as TANMedia4,
    TANMedia5 as TANMedia5,
    TANMediaClass3 as TANMediaClass3,
    TANMediaClass4 as TANMediaClass4,
    TANMediaType2 as TANMediaType2,
    TANUsageOption as TANUsageOption,
)

class HKIDN2(FinTS3Segment):
    bank_identifier: Incomplete
    customer_id: Incomplete
    system_id: Incomplete
    system_id_status: Incomplete

class HKVVB3(FinTS3Segment):
    bpd_version: Incomplete
    upd_version: Incomplete
    language: Incomplete
    product_name: Incomplete
    product_version: Incomplete

class HKTAN2(FinTS3Segment):
    tan_process: Incomplete
    task_hash_value: Incomplete
    task_reference: Incomplete
    tan_list_number: Incomplete
    further_tan_follows: Incomplete
    cancel_task: Incomplete
    challenge_class: Incomplete
    parameter_challenge_class: Incomplete

class HKTAN3(FinTS3Segment):
    tan_process: Incomplete
    task_hash_value: Incomplete
    task_reference: Incomplete
    tan_list_number: Incomplete
    further_tan_follows: Incomplete
    cancel_task: Incomplete
    challenge_class: Incomplete
    parameter_challenge_class: Incomplete
    tan_medium_name: Incomplete

class HKTAN5(FinTS3Segment):
    tan_process: Incomplete
    segment_type: Incomplete
    account: Incomplete
    task_hash_value: Incomplete
    task_reference: Incomplete
    tan_list_number: Incomplete
    further_tan_follows: Incomplete
    cancel_task: Incomplete
    sms_charge_account: Incomplete
    challenge_class: Incomplete
    parameter_challenge_class: Incomplete
    tan_medium_name: Incomplete

class HKTAN6(FinTS3Segment):
    tan_process: Incomplete
    segment_type: Incomplete
    account: Incomplete
    task_hash_value: Incomplete
    task_reference: Incomplete
    further_tan_follows: Incomplete
    cancel_task: Incomplete
    sms_charge_account: Incomplete
    challenge_class: Incomplete
    parameter_challenge_class: Incomplete
    tan_medium_name: Incomplete
    response_hhd_uc: Incomplete

class PSRD1(DataElementGroup):
    psrd: Incomplete

class HKVPP1(FinTS3Segment):
    supported_reports: Incomplete
    polling_id: Incomplete
    max_queries: Incomplete
    aufsetzpunkt: Incomplete

class EVPE(DataElementGroup):
    recipient_IBAN: Incomplete
    info_IBAN: Incomplete
    close_match_name: Incomplete
    other_identification: Incomplete
    result: Incomplete
    na_reason: Incomplete

class HIVPP1(FinTS3Segment):
    vop_id: Incomplete
    vop_id_valid_until: Incomplete
    polling_id: Incomplete
    payment_status_report_descriptor: Incomplete
    payment_status_report: Incomplete
    vop_single_result: Incomplete
    manual_authorization_notice: Incomplete
    wait_for_seconds: Incomplete

class ParameterVoP(DataElementGroup):
    max_trans: Incomplete
    notice_is_structured: Incomplete
    report_complete: Incomplete
    batch_payment_allowed: Incomplete
    multiple_allowed: Incomplete
    supported_report_formats: Incomplete
    payment_order_segment: Incomplete

class HIVPPS1(ParameterSegment):
    parameter: Incomplete

class HKVPA1(FinTS3Segment):
    vop_id: Incomplete

class HKTAN7(FinTS3Segment):
    tan_process: Incomplete
    segment_type: Incomplete
    account: Incomplete
    task_hash_value: Incomplete
    task_reference: Incomplete
    further_tan_follows: Incomplete
    cancel_task: Incomplete
    sms_charge_account: Incomplete
    challenge_class: Incomplete
    parameter_challenge_class: Incomplete
    tan_medium_name: Incomplete
    response_hhd_uc: Incomplete

class HITAN2(FinTS3Segment):
    tan_process: Incomplete
    task_hash_value: Incomplete
    task_reference: Incomplete
    challenge: Incomplete
    challenge_valid_until: Incomplete
    tan_list_number: Incomplete
    ben: Incomplete

class HITAN3(FinTS3Segment):
    tan_process: Incomplete
    task_hash_value: Incomplete
    task_reference: Incomplete
    challenge: Incomplete
    challenge_valid_until: Incomplete
    tan_list_number: Incomplete
    ben: Incomplete
    tan_medium_name: Incomplete

class HITAN5(FinTS3Segment):
    tan_process: Incomplete
    task_hash_value: Incomplete
    task_reference: Incomplete
    challenge: Incomplete
    challenge_hhduc: Incomplete
    challenge_valid_until: Incomplete
    tan_list_number: Incomplete
    ben: Incomplete
    tan_medium_name: Incomplete

class HITAN6(FinTS3Segment):
    tan_process: Incomplete
    task_hash_value: Incomplete
    task_reference: Incomplete
    challenge: Incomplete
    challenge_hhduc: Incomplete
    challenge_valid_until: Incomplete
    tan_medium_name: Incomplete

class HITAN7(FinTS3Segment):
    tan_process: Incomplete
    task_hash_value: Incomplete
    task_reference: Incomplete
    challenge: Incomplete
    challenge_hhduc: Incomplete
    challenge_valid_until: Incomplete
    tan_medium_name: Incomplete

class HKTAB4(FinTS3Segment):
    tan_media_type: Incomplete
    tan_media_class: Incomplete

class HITAB4(FinTS3Segment):
    tan_usage_option: Incomplete
    tan_media_list: Incomplete

class HKTAB5(FinTS3Segment):
    tan_media_type: Incomplete
    tan_media_class: Incomplete

class HITAB5(FinTS3Segment):
    tan_usage_option: Incomplete
    tan_media_list: Incomplete

class HITANSBase(ParameterSegment): ...

class HITANS1(HITANSBase):
    parameter: Incomplete

class HITANS2(HITANSBase):
    parameter: Incomplete

class HITANS3(HITANSBase):
    parameter: Incomplete

class HITANS4(HITANSBase):
    parameter: Incomplete

class HITANS5(HITANSBase):
    parameter: Incomplete

class HITANS6(HITANSBase):
    parameter: Incomplete

class HITANS7(HITANSBase):
    parameter: Incomplete

class HIPINS1(ParameterSegment):
    parameter: Incomplete
