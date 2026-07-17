from typing import override
from .formals import (
    AlgorithmParameterIVName as AlgorithmParameterIVName,
    AlgorithmParameterName as AlgorithmParameterName,
    CompressionFunction as CompressionFunction,
    DateTimeType as DateTimeType,
    EncryptionAlgorithm as EncryptionAlgorithm,
    EncryptionAlgorithmCoded as EncryptionAlgorithmCoded,
    HashAlgorithm as HashAlgorithm,
    IdentifiedRole as IdentifiedRole,
    KeyName as KeyName,
    KeyType as KeyType,
    OperationMode as OperationMode,
    SecurityApplicationArea as SecurityApplicationArea,
    SecurityDateTime as SecurityDateTime,
    SecurityIdentificationDetails as SecurityIdentificationDetails,
    SecurityMethod as SecurityMethod,
    SecurityProfile as SecurityProfile,
    SecurityRole as SecurityRole,
    SignatureAlgorithm as SignatureAlgorithm,
    UsageEncryption as UsageEncryption,
    UserDefinedSignature as UserDefinedSignature,
)
from .message import FinTSMessage as FinTSMessage
from .segments.message import HNSHA2 as HNSHA2, HNSHK4 as HNSHK4, HNVSD1 as HNVSD1, HNVSK3 as HNVSK3
from .types import SegmentSequence as SegmentSequence
from _typeshed import Incomplete
from fints.exceptions import FinTSError as FinTSError

class EncryptionMechanism:
    def encrypt(self, message: FinTSMessage): ...
    def decrypt(self, message: FinTSMessage): ...

class AuthenticationMechanism:
    def sign_prepare(self, message: FinTSMessage): ...
    def sign_commit(self, message: FinTSMessage): ...
    def verify(self, message: FinTSMessage): ...

class PinTanDummyEncryptionMechanism(EncryptionMechanism):
    security_method_version: Incomplete
    def __init__(self, security_method_version: int = 1) -> None: ...
    @override
    def encrypt(self, message: FinTSMessage): ...
    @override
    def decrypt(self, message: FinTSMessage): ...

class PinTanAuthenticationMechanism(AuthenticationMechanism):
    pin: Incomplete
    pending_signature: Incomplete
    security_function: Incomplete
    def __init__(self, pin) -> None: ...
    @override
    def sign_prepare(self, message: FinTSMessage): ...
    @override
    def sign_commit(self, message: FinTSMessage): ...
    @override
    def verify(self, message: FinTSMessage): ...

class PinTanOneStepAuthenticationMechanism(PinTanAuthenticationMechanism):
    security_function: str
    def __init__(self, *args, **kwargs) -> None: ...

class PinTanTwoStepAuthenticationMechanism(PinTanAuthenticationMechanism):
    client: Incomplete
    security_function: Incomplete
    def __init__(self, client, security_function, *args, **kwargs) -> None: ...
