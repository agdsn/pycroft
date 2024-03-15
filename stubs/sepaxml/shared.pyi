from .utils import decimal_str_to_int as decimal_str_to_int, int_to_decimal_str as int_to_decimal_str, make_msg_id as make_msg_id
from .validation import try_valid_xml as try_valid_xml
from _typeshed import Incomplete

class SepaPaymentInitn:
    schema: Incomplete
    msg_id: Incomplete
    clean: Incomplete
    def __init__(self, config, schema, clean: bool = True) -> None: ...
    def export(self, validate: bool = True, pretty_print: bool = False) -> bytes: ...
