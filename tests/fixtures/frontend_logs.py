from .dummy import logging
from . import permissions


# These datasets contain users with permissions plus a room and a user
# log tied to the dummy user and his room.
datasets = (
    permissions.datasets
    | {logging.RoomLogEntryData, logging.UserLogEntryData}
)
