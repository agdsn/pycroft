from collections.abc import Sequence
from datetime import datetime, timedelta

from schwifty import IBAN
from sepaxml import SepaTransfer
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from pycroft import config
from pycroft.helpers.utc import ensure_tz
from pycroft.model.finance import BankAccountActivity
from pycroft.model.user import User

from .transaction_crud import simple_transaction


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
        bic = activity.other_routing_number or IBAN(activity.other_account_number).bic.compact
        payment = {
            "name": activity.other_name,
            "IBAN": activity.other_account_number,
            "BIC": bic,
            "amount": int(activity.amount * 100),
            "execution_date": datetime.now().date(),
            "description": f"Rücküberweisung nicht zuordenbarer Überweisung vom {activity.posted_on} mit Referenz {activity.reference}"[
                :140
            ],
        }
        sepa.add_payment(payment)

    return sepa.export()


def attribute_activities_as_returned(
    session: Session, activities: list[BankAccountActivity], author: User
) -> None:
    for activity in activities:
        debit_account = config.non_attributable_transactions_account
        credit_account = activity.bank_account.account

        transaction = simple_transaction(
            description=activity.reference,
            debit_account=debit_account,
            credit_account=credit_account,
            amount=activity.amount,
            author=author,
            valid_on=activity.valid_on,
            confirmed=False,
        )
        activity.split = next(
            split for split in transaction.splits if split.account_id == credit_account.id
        )
        session.add(activity)
