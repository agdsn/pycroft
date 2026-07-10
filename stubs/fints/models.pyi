from _typeshed import Incomplete
from typing import NamedTuple

class SEPAAccount(NamedTuple):
    iban: Incomplete
    bic: Incomplete
    accountnumber: Incomplete
    subaccount: Incomplete
    blz: Incomplete

class Saldo(NamedTuple):
    account: Incomplete
    date: Incomplete
    value: Incomplete
    currency: Incomplete

class Holding(NamedTuple):
    ISIN: Incomplete
    name: Incomplete
    market_value: Incomplete
    value_symbol: Incomplete
    valuation_date: Incomplete
    pieces: Incomplete
    total_value: Incomplete
    acquisitionprice: Incomplete

class Amount(NamedTuple):
    amount: Incomplete
    currency: Incomplete

class Transaction(NamedTuple):
    data: Incomplete
