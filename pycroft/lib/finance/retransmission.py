#  Copyright (c) 2026. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details

from sqlalchemy.orm import Session

from pycroft.lib.finance import estimate_balance
from pycroft.model.base import IntegerIdModel
from pycroft.model.finance import Retransmission, RetransmissionStateEnum
from pycroft.model.user import User
from tests.lib.infrastructure.conftest import switch


def create_retransmission(session: Session, account: User, owner: str, iban: str, bic: str) -> Retransmission:
    amount = estimate_balance(session, account, )
    retransmission = Retransmission(account_id=account.id, owner=owner, iban=iban, bic=bic, amount=account.balance)
    session.add(retransmission)

    return retransmission

def approve_retransmission(session: Session, retransmission: Retransmission, account: User) -> Retransmission:
    match retransmission.state:
        case RetransmissionStateEnum.pending:
            retransmission.ledger_1.id = account.id
            retransmission.state = RetransmissionStateEnum.processing

        case RetransmissionStateEnum.processing:
            retransmission.ledger_2_id = account.id
            retransmission.state = RetransmissionStateEnum.done
        case _:
            raise ValueError
    session.add(retransmission)

    return retransmission

def decline_retransmission(session: Session, retransmission: Retransmission, account: User, reson: str) -> Retransmission:
    match retransmission.state:
        case RetransmissionStateEnum.pending:
            retransmission.ledger_1.id = account.id
            retransmission.state = RetransmissionStateEnum.declined

        case RetransmissionStateEnum.processing:
            retransmission.ledger_2_id = account.id
            retransmission.state = RetransmissionStateEnum.declined
        case _:
            raise ValueError

    retransmission.reason = reson
    session.add(retransmission)

    return retransmission
