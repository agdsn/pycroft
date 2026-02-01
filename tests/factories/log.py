import factory

from pycroft.model.logging import UserLogEntry, RoomLogEntry
from .base import BaseFactory
from .facilities import RoomFactory
from .user import UserFactory


class UserLogEntryFactory(BaseFactory):
    class Meta:
        model = UserLogEntry

    message = factory.Faker('paragraph')
    author = factory.SubFactory(UserFactory)
    user = factory.SubFactory(UserFactory)
    created_at = None


class RoomLogEntryFactory(BaseFactory):
    class Meta:
        model = RoomLogEntry

    message = factory.Faker('paragraph')
    author = factory.SubFactory(UserFactory)
    room = factory.SubFactory(RoomFactory)
