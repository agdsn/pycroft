from .shared import SepaPaymentInitn as SepaPaymentInitn
from .utils import ADDRESS_MAPPING as ADDRESS_MAPPING, int_to_decimal_str as int_to_decimal_str, make_id as make_id

class SepaDD(SepaPaymentInitn):
    root_el: str
    def __init__(self, config, schema: str = 'pain.008.003.02', clean: bool = True) -> None: ...
    def check_config(self, config): ...
    def check_payment(self, payment): ...
    def add_payment(self, payment) -> None: ...
