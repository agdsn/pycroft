import abc
import re

import pytest
from sqlalchemy.orm import Session

from pycroft.helpers.i18n import localized
from pycroft.lib.user import edit_address
from pycroft.model.logging import UserLogEntry
from pycroft.model.user import User
from ...factories import UserFactory


class TestUserAddressChange(abc.ABC):
    __test__ = False

    @pytest.fixture(scope="class")
    def address_args(self) -> dict[str, str | None]:
        return {
            'street': "Blahstraße",
            'number': "5",
            'addition': "Keller",
            'zip_code': "01217",
            'city': "Dresden",
            'state': None,
            'country': None,
        }

    @abc.abstractmethod
    def user(self, class_session: Session) -> User:
        ...

    @pytest.fixture(scope="class", autouse=True)
    def edited_address(self, class_session, user, processor, address_args):
        assert not user.has_custom_address  # fixture sanity assertion
        edit_address(user, processor, **address_args)

    def test_address_values_correct(
        self, user: User, address_args: dict[str, str | None]
    ):
        address = user.address
        for key, val in address_args.items():
            if key == "country":
                assert address.country == val or "Germany"
                continue
            assert getattr(address, key) == (val or "")

    RE_MESSAGE = re.compile("changed address", re.I)

    def test_log_entry(self, user, processor):
        le: UserLogEntry = user.latest_log_entry
        assert le and le.author == processor
        assert self.RE_MESSAGE.search(localized(le.message))

    def test_user_address_change(
        self, user: User, address_args: dict[str], processor: User, session: Session
    ):
        if user.room:
            assert user.has_custom_address


class TestUserWithRoomAddressChange(TestUserAddressChange):
    __test__ = True

    @pytest.fixture(scope="class")
    def user(self, class_session: Session) -> User:
        return UserFactory()

    def test_user_has_custom_address(self, user):
        assert user.has_custom_address


class TestUserWithoutRoomAddressChange(TestUserAddressChange):
    __test__ = True

    @pytest.fixture(scope="class")
    def user(self, class_session: Session) -> User:
        return UserFactory.create(without_room=True)

    def test_user_has_no_custom_address(self, user):
        assert not user.has_custom_address
