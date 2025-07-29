import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from pycroft.lib.user_deletion import scrub_all_mails, scrub_mail, scrubbable_mails
from pycroft.model.scrubbing import ScrubLog
from pycroft.model.user import User
from tests.assertions import assert_one


def test_scrubbable_mail_found(session: Session, user_archivable: User):
    assert scrubbable_mails(session).all() == [user_archivable]


def test_scrubbing_scrubs_mail(user_archivable: User, processor: User, session: Session):
    scrub_mail(session, user=user_archivable, author=processor)
    session.flush()
    session.refresh(user_archivable)

    assert user_archivable.email is None
    log_entries = user_archivable.log_entries
    le = assert_one(log_entries)
    assert "scrubbed" in le.message.lower()
    assert "mail" in le.message.lower()

    sl = session.scalars(select(ScrubLog)).one()
    assert sl.scrubber == "mail"
    match sl.info:
        case {"user_id": user_archivable.id}:
            pass
        case _:
            pytest.fail(
                f"expected scrublog.info to match `user_id: {user_archivable.id}`, got {sl!r}"
            )


def test_bulk_scrubbing_scrubs_mail(
    users_archivable: list[User], users_notarchivable: list[User], processor: User, session: Session
):
    scrub_all_mails(session, author=processor)
