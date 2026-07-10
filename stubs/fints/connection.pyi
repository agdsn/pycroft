from .exceptions import (
    FinTSError as FinTSError,
    FinTSClientError as FinTSClientError,
    FinTSClientPINError as FinTSClientPINError,
    FinTSClientTemporaryAuthError as FinTSClientTemporaryAuthError,
    FinTSSCARequiredError as FinTSSCARequiredError,
    FinTSDialogError as FinTSDialogError,
    FinTSDialogStateError as FinTSDialogStateError,
    FinTSDialogOfflineError as FinTSDialogOfflineError,
    FinTSDialogInitError as FinTSDialogInitError,
    FinTSConnectionError as FinTSConnectionError,
    FinTSUnsupportedOperation as FinTSUnsupportedOperation,
    FinTSNoResponseError as FinTSNoResponseError,
)
from .message import FinTSInstituteMessage as FinTSInstituteMessage, FinTSMessage as FinTSMessage
from .types import SegmentSequence as SegmentSequence
from _typeshed import Incomplete
from fints.utils import Password as Password, log_configuration as log_configuration

logger: Incomplete

def reduce_message_for_log(msg): ...

class FinTSHTTPSConnection:
    url: Incomplete
    session: Incomplete
    def __init__(self, url) -> None: ...
    def send(self, msg: FinTSMessage): ...
