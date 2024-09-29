#  Copyright (c) 2023. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details

import typing as t
from datetime import date

from mt940.models import Transaction as MT940Transaction

from pycroft.external_services.fints import FinTS3Client, StatementError
from pycroft.model.finance import BankAccount


def get_fints_client(
    *,
    product_id: str,
    user_id: str,
    secret_pin: str,
    bank_account: BankAccount,
    **kwargs: t.Any,
) -> FinTS3Client:
    return FinTS3Client(
        bank_identifier=bank_account.routing_number,
        user_id=user_id,
        pin=secret_pin,
        server=bank_account.fints_endpoint,
        product_id=product_id,
        **kwargs,
    )


def get_fints_transactions(
    *,
    start_date: date,
    end_date: date,
    bank_account: BankAccount,
    fints_client: FinTS3Client,
) -> tuple[list[MT940Transaction], list[StatementError]]:
    """Get the transactions from FinTS

    External service dependencies:

    - FinTS (:module:`pycroft.external_services.fints`)
    """
    acc = next(
        (a for a in fints_client.get_sepa_accounts() if a.iban == bank_account.iban),
        None,
    )
    if acc is None:
        raise KeyError(f"BankAccount with IBAN {bank_account.iban} not found.")
    return fints_client.get_filtered_transactions(acc, start_date, end_date)
