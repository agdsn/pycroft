import pytest

from pycroft.lib import user as UserHelper
from pycroft.model.user import RoomHistoryEntry
from tests import FactoryDataTestBase, factories

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


class SimilarUserTestCase(FactoryDataTestBase):
    def create_factories(self):
        super().create_factories()
        # We need a user in the same room
        self.room = factories.RoomFactory()
        self.similar_user_this_room = factories.UserFactory(room=self.room, name="Tobias Fuenke")

        self.similar_user_room_history = factories.UserFactory(name="Tobias")
        self.session.add(RoomHistoryEntry(room=self.room, user=self.similar_user_room_history))

        # nonsimilar users (same room / room history)
        factories.UserFactory(room=self.room, name="Other dude")
        self.session.add(RoomHistoryEntry(room=self.room,
                                          user=factories.UserFactory(name="Other dude")))

    def test_similar_users_found(self):
        assert UserHelper.find_similar_users("Tobias Fünke", self.room, THRESHOLD) \
               == [self.similar_user_this_room, self.similar_user_room_history]
