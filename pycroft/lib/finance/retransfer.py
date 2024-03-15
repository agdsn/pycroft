from collections.abc import Sequence
from datetime import datetime, timedelta

from sepaxml import SepaTransfer
from sqlalchemy import select
from sqlalchemy.orm import joinedload, Session

from pycroft import config
from pycroft.helpers.utc import ensure_tz
from pycroft.model.finance import BankAccountActivity


def get_activities_to_return(session: Session) -> Sequence[BankAccountActivity]:
    statement = (
        select(BankAccountActivity)
        .options(joinedload(BankAccountActivity.bank_account))
        .filter(BankAccountActivity.transaction_id.is_(None))
        .filter(BankAccountActivity.amount > 0)
        .filter(BankAccountActivity.imported_at < ensure_tz(datetime.utcnow() - timedelta(days=14)))
    )

    return session.scalars(statement).all()


def generate_activities_return_sepaxml(activities: list[BankAccountActivity]) -> bytes:
    transfer_config: dict = {
        "name": config.membership_fee_bank_account.owner,
        "IBAN": config.membership_fee_bank_account.iban,
        "BIC": config.membership_fee_bank_account.bic,
        "batch": False,
        "currency": "EUR",
    }
    sepa = SepaTransfer(transfer_config, clean=False)

    for activity in activities:
        payment = {
            "name": activity.other_name,
            "IBAN": activity.other_account_number,
            "BIC": activity.other_routing_number,
            "amount": int(activity.amount * 100),
            "execution_date": datetime.now().date(),
            "description": f"Rücküberweisung nicht zuordenbarer Überweisung vom {activity.posted_on} mit Referenz {activity.reference}",
        }
        sepa.add_payment(payment)

    return sepa.export()
