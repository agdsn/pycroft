#  Copyright (c) 2023. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
from contextlib import contextmanager
from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from dateutil.utils import today
from fints.client import FinTS3PinTanClient
from fints.connection import FinTSHTTPSConnection
from fints.message import FinTSMessage, FinTSInstituteMessage
from fints.models import SEPAAccount
from fints.utils import Password

from pycroft.external_services.fints import FinTS3Client
from pycroft.lib.finance.fints import get_fints_transactions
from tests.factories.finance import BankAccountFactory as BankAccountFactory_


def test_fints_connection(default_fints_client_args, default_transaction_args):
    bank_account = BankAccountFactory.build(iban="DE61850503003120219540")
    fints_client = StubFintsClient(
        **default_fints_client_args,
        bank_identifier=bank_account.routing_number,
        server=bank_account.fints_endpoint,
    )

    transactions, errors = get_fints_transactions(
        **default_transaction_args,
        bank_account=bank_account,
        fints_client=fints_client,
    )
    assert transactions == []
    assert errors == []


def test_transactions_unknown_iban(default_fints_client_args, default_transaction_args):
    bank_account = BankAccountFactory.build()
    fints_client = StubFintsClient(
        **default_fints_client_args,
        bank_identifier=bank_account.routing_number,
        server=bank_account.fints_endpoint,
    )

    with pytest.raises(KeyError, match="BankAccount with IBAN.*not found"):
        get_fints_transactions(
            **default_transaction_args,
            bank_account=bank_account,
            fints_client=fints_client,
        )


@pytest.fixture(scope="session")
def default_transaction_args() -> dict:
    return {
        "start_date": today() - timedelta(days=30),
        "end_date": today(),
    }


@pytest.fixture(scope="session")
def default_fints_client_args() -> dict:
    return {
        "product_id": "1",
        "user_id": 1,
        "pin": "123456",
    }


class BankAccountFactory(BankAccountFactory_):
    fints_endpoint = "https://banking-sn5.s-fints-pt-sn.de/fints30"
    routing_number = "85050300"


class StubHTTPSConnection(FinTSHTTPSConnection):
    def send(self, msg: FinTSMessage):
        # response = base64.b64decode(r.content.decode('iso-8859-1'))
        return FinTSInstituteMessage(segments="Test!")


class StubFintsClient(FinTS3Client):
    def __init__(self, bank_identifier, user_id, pin, server, *args, **kwargs):
        self.pin = Password(pin) if pin is not None else pin
        self._pending_tan = None
        # ↓ Skip this line of FinTS3PinTanClient.__init__ ↓
        # self.connection = FinTSHTTPSConnection(server)
        self.connection = StubHTTPSConnection(server)
        self.allowed_security_functions = []
        self.selected_security_function = None
        self.selected_tan_medium = None
        self._bootstrap_mode = True
        super(FinTS3PinTanClient, self).__init__(
            *args,
            **kwargs,
            bank_identifier=bank_identifier,
            user_id=user_id,
        )

    @contextmanager
    def _get_dialog(self, lazy_init=False):
        # Usually returns FinTSDialog
        yield MagicMock()

    def get_sepa_accounts(self):
        return [
            SEPAAccount(
                iban="DE61850503003120219540",
                bic=None,
                accountnumber=None,
                subaccount=None,
                blz=None,
            )
        ]

    def _find_highest_supported_command(self, *segment_classes, **kwargs):
        return segment_classes[-1]
