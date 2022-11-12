import pytest

from pycroft.helpers.interval import starting_from
from pycroft.helpers.interval import Interval
from pycroft.helpers.utc import DateTimeTz
from pycroft.lib import user as UserHelper
from pycroft.model.facilities import Room
from pycroft.model.user import RoomHistoryEntry, User
from tests import factories

THRESHOLD = 0.6


@pytest.mark.parametrize("one,other", [
    ("Hans", "Hans_"),
    ("  Franz", "Franz"),
    ("Tobias Fuenke", "Tobias Fünke"),
    ("Tobias Fünke", "Tobias"),
    ("Richard Paul Astley", "Rick Astley"),
])
def test_similar_names(one, other):
    assert UserHelper.are_names_similar(one, other, THRESHOLD)


@pytest.mark.parametrize("one,other", [
    ("Hans", "Definitiv ganz und gar nicht Hans"),
    ("Tobias Fuenke", "Fünke Tobias"),
    ("Lukas Juhrich der Große", "Lucas der geile Hecht"),
])
def test_nonsimilar_names(one, other):
    assert not UserHelper.are_names_similar(one, other, THRESHOLD)


class TestSimilarUsers:
    @pytest.fixture(scope="class")
    def room(self, class_session) -> Room:
        return factories.RoomFactory()

    @pytest.fixture(scope="class")
    def inhabitant(self, class_session, room) -> User:
        return factories.UserFactory(room=room, name="Tobias Fuenke")

    @pytest.fixture(scope="class")
    def interval(self, utcnow) -> Interval[DateTimeTz]:
        return starting_from(utcnow)

    @pytest.fixture(scope="class", autouse=True)
    def similar_former_inhabitant(self, class_session, room, interval) -> User:
        user = factories.UserFactory(name="Tobias")
        class_session.add(
            RoomHistoryEntry(room=room, user=user, active_during=interval)
        )
        return user

    @pytest.fixture(scope="class", autouse=True)
    def nonsimilar_former_inhabitants(self, class_session, room, interval) -> None:
        factories.UserFactory(room=room, name="Other dude")
        class_session.add(
            RoomHistoryEntry(
                room=room,
                user=factories.UserFactory(name="Yet someone else"),
                active_during=interval,
            )
        )

    def test_similar_users_found(self, room, inhabitant, similar_former_inhabitant):
        assert set(UserHelper.find_similar_users("Tobias Fünke", room, THRESHOLD)) == {
            inhabitant,
            similar_former_inhabitant,
        }
