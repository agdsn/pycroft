from datetime import datetime
import pytest
from sqlalchemy.orm import Session

from pycroft.helpers.interval import closedopen
from pycroft.model.config import Config
from pycroft.model.user import PropertyGroup, User
from tests import factories as f


@pytest.fixture(scope="module")
def group_do_not_archive(module_session: Session) -> PropertyGroup:
    return f.PropertyGroupFactory.create(
        name="Do Not Archive Group", granted={"do-not-archive"}, denied=set()
    )


@pytest.fixture(autouse=True)
def freeze(freezer) -> None:
    freezer.move_to("2025-01-01")


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


@pytest.fixture(scope="module")
def users_archivable(module_session: Session, config: Config) -> list[User]:
    # TODO: user wtih membership
    return f.UserFactory.create_batch(
        10,
        registered_at=datetime(2020, 7, 1),
        with_membership=True,
        membership__active_during=closedopen(datetime(2020, 7, 1), datetime(2021, 11, 25)),
        membership__group=config.member_group,
        without_room=True,
    )


@pytest.fixture(scope="module", autouse=True)
def users_do_not_archive(
    module_session: Session, config: Config, group_do_not_archive: PropertyGroup
) -> list[User]:
    """
    Create a user with a membership in a group that has the do-not-archive
    property.
    """
    # TODO wayyy better example set! instead of making all `do-not-archive`,
    # we would want them to have different membership ranges, also additional memberships;
    # also edge-cases like upcoming memberships or on-new-years membership terminations
    beginning = datetime(2020, 7, 1)
    users = f.UserFactory.create_batch(
        10,
        registered_at=beginning,
        with_membership=True,
        membership__active_during=closedopen(beginning, datetime(2021, 11, 25)),
        membership__group=config.member_group,
        without_room=True,
    )
    for user in users:
        f.MembershipFactory.create(
            user=user,
            group=group_do_not_archive,
            active_during=closedopen(beginning, None),
        )
    return users
