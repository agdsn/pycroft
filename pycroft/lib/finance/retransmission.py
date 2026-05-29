#  Copyright (c) 2026. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details

from sqlalchemy.orm import Session

from pycroft.helpers import date
from pycroft.lib.finance import estimate_balance
from pycroft.model.finance import Retransmission, RetransmissionStateEnum
from pycroft.model.user import User


def create_retransmission(session: Session, user: User, owner: str, iban: str, bic: str, bis: date) -> Retransmission:
    amount = estimate_balance(session, user, bis)
    retransmission = Retransmission(user_id=user.id, owner=owner, iban=iban, bic=bic, amount=amount, state=RetransmissionStateEnum.pending)
    session.add(retransmission)
    session.commit()
    return retransmission

def approve_retransmission(session: Session, retransmission: Retransmission, account: User) -> Retransmission:
    match retransmission.state:
        case RetransmissionStateEnum.pending:
            retransmission.ledger_1_id = account.id
            retransmission.state = RetransmissionStateEnum.processing

        case RetransmissionStateEnum.processing:
            retransmission.ledger_2_id = account.id
            retransmission.state = RetransmissionStateEnum.done
        case _:
            raise ValueError
    session.commit()
    return retransmission

def decline_retransmission(session: Session, retransmission: Retransmission, account: User, reson: str) -> Retransmission:
    match retransmission.state:
        case RetransmissionStateEnum.pending:
            retransmission.ledger_1_id = account.id
            retransmission.state = RetransmissionStateEnum.declined

        case RetransmissionStateEnum.processing:
            retransmission.ledger_2_id = account.id
            retransmission.state = RetransmissionStateEnum.declined
        case _:
            raise ValueError

    retransmission.reason = reson
    session.add(retransmission)
    session.commit()

    return retransmission
