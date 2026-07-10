import types
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
from .connection import FinTSConnectionError as FinTSConnectionError
from .formals import (
    CUSTOMER_ID_ANONYMOUS as CUSTOMER_ID_ANONYMOUS,
    Language2 as Language2,
    SystemIDStatus as SystemIDStatus,
)
from .message import (
    FinTSCustomerMessage as FinTSCustomerMessage,
    MessageDirection as MessageDirection,
)
from .segments.auth import HKIDN2 as HKIDN2, HKVVB3 as HKVVB3
from .segments.dialog import HKEND1 as HKEND1
from .segments.message import HNHBK3 as HNHBK3, HNHBS1 as HNHBS1
from .utils import (
    compress_datablob as compress_datablob,
    decompress_datablob as decompress_datablob,
)
from _typeshed import Incomplete

logger: Incomplete
DIALOG_ID_UNASSIGNED: str
DATA_BLOB_MAGIC: bytes

class FinTSDialog:
    client: Incomplete
    next_message_number: Incomplete
    messages: Incomplete
    auth_mechanisms: Incomplete
    enc_mechanism: Incomplete
    open: bool
    need_init: bool
    lazy_init: Incomplete
    dialog_id: Incomplete
    paused: bool
    def __init__(
        self,
        client: Incomplete | None = None,
        lazy_init: bool = False,
        enc_mechanism: Incomplete | None = None,
        auth_mechanisms: Incomplete | None = None,
    ) -> None: ...
    def __enter__(self): ...
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> None: ...
    def init(self, *extra_segments): ...
    def end(self) -> None: ...
    def send(self, *segments, **kwargs): ...
    def new_customer_message(self): ...
    def finish_message(self, message) -> None: ...
    def pause(self): ...
    @classmethod
    def create_resume(cls, client, blob): ...
