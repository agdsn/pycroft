#  Copyright (c) 2024. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
from sqlalchemy.orm import Session

from pycroft.model.mpsk_client import MPSKClient
from pycroft.model.user import User
from pycroft.lib.logging import log_user_event
from pycroft.helpers.i18n import deferred_gettext


def mpsk_delete(session: Session, *, mpsk_client: MPSKClient, processor: User) -> None:
    message = deferred_gettext("Deleted mpsk client '{}'.").format(mpsk_client.name)
    log_user_event(author=processor, user=mpsk_client.owner, message=message.to_json())

    session.delete(mpsk_client)


def change_mac(session: Session, *, client: MPSKClient, mac: str, processor: User) -> MPSKClient:
    """
    This method will change the mac address of the given mpsks client to the new
    mac address.

    :param session: session to use with the database.
    :param client: the mpsks which should become a new mac address.
    :param mac: the new mac address.
    :param processor: the user who initiated the mac address change.
    :return: the changed interface with the new mac address.
    """
    old_mac = client.mac
    client.mac = mac
    message = deferred_gettext("Changed MAC address from {} to {}.").format(old_mac, mac)
    if client.owner:
        log_user_event(message.to_json(), processor, client.owner)
    session.add(client)
    return client


def mpsk_client_create(
    session: Session, *, owner: User, name: str, mac: str, processor: User
) -> MPSKClient:
    """
    creates a mpsks client for a given user with a mac address.

    :param session: session to use with the database.
    :param owner: the user who initiated the mac address change.
    :param name: the name of the mpsks client.
    :param mac: the new mac address.
    :param processor: the user who initiated the mac address change.
    """
    client = MPSKClient(name=name, owner_id=owner.id, mac=mac)

    session.add(client)

    message = deferred_gettext("Created MPSK Client '{name}' with MAC: {mac}.").format(
        name=client.name,
        mac=client.mac,
    )

    log_user_event(author=processor, user=owner, message=message.to_json())

    return client


def mpsk_edit(
    session: Session, *, client: MPSKClient, owner: User, name: str, mac: str, processor: User
) -> None:
    if client.name != name:
        message = deferred_gettext("Changed name of client '{}' to '{}'.").format(client.name, name)
        client.name = name

        log_user_event(author=processor, user=owner, message=message.to_json())

    if client.owner_id != owner.id:
        message = deferred_gettext("Transferred Host '{}' to {}.").format(client.name, owner.id)
        log_user_event(author=processor, user=client.owner, message=message.to_json())

        message = deferred_gettext("Transferred Host '{}' from {}.").format(
            client.name, client.owner.id
        )
        log_user_event(author=processor, user=owner, message=message.to_json())

        client.owner = owner

    if client.mac != mac:
        message = deferred_gettext("Changed MAC address of client '{}' to '{}'.").format(
            client.name, mac
        )
        log_user_event(author=processor, user=owner, message=message.to_json())
        client.mac = mac
    session.add(client)
