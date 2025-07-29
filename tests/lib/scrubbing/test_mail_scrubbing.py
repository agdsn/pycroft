# TODO archivable member
from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from pycroft.helpers.interval import closedopen
from pycroft.lib.user_deletion import scrub_mail, scrubbable_mails
from pycroft.model.config import Config
from pycroft.model.scrubbing import ScrubLog
from pycroft.model.user import PropertyGroup, User
from tests import factories as f
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


@pytest.fixture(scope="module")
def user_archivable(module_session: Session, config: Config) -> User:
    # TODO: user wtih membership
    return f.UserFactory.create(
        registered_at=datetime(2020, 7, 1),
        with_membership=True,
        membership__active_during=closedopen(datetime(2020, 7, 1), datetime(2021, 11, 25)),
        membership__group=config.member_group,
        without_room=True,
    )


@pytest.fixture(scope="module", autouse=True)
def user_do_not_archive(
    module_session: Session, config: Config, group_do_not_archive: PropertyGroup
) -> User:
    """
    Create a user with a membership in a group that has the do-not-archive
    property.
    """
    # TODO _very old_ membership, but also mem in a group
    user = f.UserFactory.create(
        registered_at=datetime(2020, 7, 1),
        with_membership=True,
        membership__active_during=closedopen(datetime(2020, 7, 1), datetime(2021, 11, 25)),
        membership__group=config.member_group,
        without_room=True,
    )
    f.MembershipFactory.create(
        user=user, group=group_do_not_archive, active_during=closedopen(datetime(2020, 7, 1), None)
    )
    return user
