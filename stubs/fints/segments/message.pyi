from .base import FinTS3Segment as FinTS3Segment
from _typeshed import Incomplete
from fints.fields import (
    CodeField as CodeField,
    DataElementField as DataElementField,
    DataElementGroupField as DataElementGroupField,
    SegmentSequenceField as SegmentSequenceField,
    ZeroPaddedNumericField as ZeroPaddedNumericField,
)
from fints.formals import (
    Certificate as Certificate,
    CompressionFunction as CompressionFunction,
    EncryptionAlgorithm as EncryptionAlgorithm,
    HashAlgorithm as HashAlgorithm,
    KeyName as KeyName,
    ReferenceMessage as ReferenceMessage,
    SecurityApplicationArea as SecurityApplicationArea,
    SecurityDateTime as SecurityDateTime,
    SecurityIdentificationDetails as SecurityIdentificationDetails,
    SecurityProfile as SecurityProfile,
    SecurityRole as SecurityRole,
    SignatureAlgorithm as SignatureAlgorithm,
    UserDefinedSignature as UserDefinedSignature,
)

class HNHBK3(FinTS3Segment):
    message_size: Incomplete
    hbci_version: Incomplete
    dialog_id: Incomplete
    message_number: Incomplete
    reference_message: Incomplete

class HNHBS1(FinTS3Segment):
    message_number: Incomplete

class HNVSK3(FinTS3Segment):
    security_profile: Incomplete
    security_function: Incomplete
    security_role: Incomplete
    security_identification_details: Incomplete
    security_datetime: Incomplete
    encryption_algorithm: Incomplete
    key_name: Incomplete
    compression_function: Incomplete
    certificate: Incomplete

class HNVSD1(FinTS3Segment):
    data: Incomplete

class HNSHK4(FinTS3Segment):
    security_profile: Incomplete
    security_function: Incomplete
    security_reference: Incomplete
    security_application_area: Incomplete
    security_role: Incomplete
    security_identification_details: Incomplete
    security_reference_number: Incomplete
    security_datetime: Incomplete
    hash_algorithm: Incomplete
    signature_algorithm: Incomplete
    key_name: Incomplete
    certificate: Incomplete

class HNSHA2(FinTS3Segment):
    security_reference: Incomplete
    validation_result: Incomplete
    user_defined_signature: Incomplete
