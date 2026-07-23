#  Copyright (c) 2026. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details

from __future__ import annotations

import datetime
from io import BytesIO
from os.path import join, dirname

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

# ---------------------------------------------------------------------------
# Asset paths – adjust to wherever your project stores them
# ---------------------------------------------------------------------------
ASSETS_DIRECTORY = join(dirname(__file__), 'assets')
ASSETS_LOGO_FILENAME = join(ASSETS_DIRECTORY, 'logo.png')
ASSETS_EMAIL_FILENAME = join(ASSETS_DIRECTORY, 'email.png')
ASSETS_FACEBOOK_FILENAME = join(ASSETS_DIRECTORY, 'facebook.png')
ASSETS_TWITTER_FILENAME = join(ASSETS_DIRECTORY, 'twitter.png')
ASSETS_WEB_FILENAME = join(ASSETS_DIRECTORY, 'web.png')
ASSETS_HOUSE_FILENAME = join(ASSETS_DIRECTORY, 'house.png')

from sqlalchemy.orm import Session

from pycroft.helpers import date
from pycroft.lib.finance import estimate_balance
from pycroft.model.finance import Retransmission, RetransmissionStateEnum
from pycroft.model.user import User


def create_retransmission(session: Session, user: User, owner: str, iban: str, bic: str, until=date.date.today()) -> Retransmission:
    amount = estimate_balance(session, user, until)

    if amount <= 0:
        raise ValueError("User has no money to retransmit")

    retransmissions = session.query(Retransmission).filter(
        Retransmission.user == user,
        Retransmission.state.in_([
        RetransmissionStateEnum.pending,
        RetransmissionStateEnum.processing
    ])
    ).all()

    if len(retransmissions) > 0:
        raise LookupError
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
