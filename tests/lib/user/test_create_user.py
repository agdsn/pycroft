import dataclasses
from datetime import date

import pytest

from pycroft.lib.user import create_user
from pycroft.model.logging import LogEntry
from tests import factories
from tests.assertions import assert_one

from .assertions import (
    assert_account_name,
    assert_logmessage_startswith,
    assert_mail_reasonable,
    assert_membership_groups,
)


@dataclasses.dataclass
class UserData:
    name: str
    login: str
    email: str
    mac: str
    birthdate: date


class TestUserCreation:
    @pytest.fixture(scope="class")
    def member_group(self, class_session):
        return factories.property.MemberPropertyGroupFactory.create()

    @pytest.fixture(scope="class")
    def room(self, class_session):
        return factories.RoomFactory.create(patched_with_subnet=True)

    @pytest.fixture(scope="class")
    def user_data(self) -> UserData:
        return UserData(
            name="Hans",
            login="hans66",
            email="hans@hans.de",
            mac="12:11:11:11:11:11",
            birthdate=date.fromisoformat("1990-01-01"),
        )

    @pytest.fixture(scope="class", autouse=True)
    def new_user(self, class_session, user_data, room, processor, member_group):
        from unittest.mock import patch

        with patch("pycroft.lib.user.user_send_mails"):
            new_user, _ = create_user(
                user_data.name,
                user_data.login,
                user_data.email,
                user_data.birthdate,
                processor=processor,
                groups=(member_group,),
                address=room.address,
            )
        return new_user

    def test_user_base_data(self, new_user, user_data, room):
        assert new_user.name == user_data.name
        assert new_user.login == user_data.login
        assert new_user.email == user_data.email

    def test_user_address(self, new_user, user_data, room):
        # TODO fix signature of `create_user` and also check for explicitly supplied address.
        assert new_user.address == room.address
        assert not new_user.has_custom_address

    def test_user_memberships(self, new_user, member_group):
        assert_membership_groups(new_user.active_memberships(), [member_group])

    def test_unix_account(self, new_user):
        assert new_user.unix_account.home_directory == f"/home/{new_user.login}"

    def test_log_entries(self, new_user):
        assert len(new_user.log_entries) == 2
        first, second = new_user.log_entries  # possibly created the exact same time

        def _assert(first: LogEntry, second: LogEntry):
            assert_logmessage_startswith(first, "Added to group Mitglied")
            assert_logmessage_startswith(second, "User created")

        try:
            _assert(first, second)
        except AssertionError:
            _assert(second, first)

    def test_finance_account(self, new_user):
        assert_account_name(new_user.account, f"User {new_user.id}")
        assert new_user.account is not None
        assert new_user.account.balance == 0

    def test_mail_content(self, processor, member_group, room, mail_capture):
        create_user(
            "Jane Doe",
            "janed",
            "jane.doe@example.org",
            date.fromisoformat("2000-03-14"),
            processor=processor,
            groups=(member_group,),
            address=room.address,
        )

        assert_mail_reasonable(assert_one(mail_capture), subject_re="Willkommen")
