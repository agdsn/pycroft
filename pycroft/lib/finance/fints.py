#  Copyright (c) 2023. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details

from datetime import date

from fints.client import FinTS3PinTanClient
from fints.models import Transaction as FinTSTransaction
from mt940.models import Transaction as MT940Transaction

from pycroft.model.finance import BankAccount


def get_fints_transactions(
    *,
    start_date: date,
    end_date: date,
    bank_account: BankAccount,
    fints_client: FinTS3PinTanClient,
) -> list[MT940Transaction | FinTSTransaction]:
    acc = next(
        (a for a in fints_client.get_sepa_accounts() if a.iban == bank_account.iban),
        None,
    )
    if acc is None:
        raise KeyError(f"BankAccount with IBAN {bank_account.iban} not found.")
    return fints_client.get_transactions(acc, start_date, end_date)
