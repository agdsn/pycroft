import re
import typing as t
from datetime import timedelta, date
from difflib import SequenceMatcher

from sqlalchemy import func

from pycroft import config
from pycroft.helpers import utc
from pycroft.helpers.i18n import deferred_gettext
from pycroft.helpers.interval import closed
from pycroft.lib.logging import log_user_event, log_event
from pycroft.lib.mail import MemberRequestDeniedTemplate
from pycroft.lib.membership import make_member_of
from pycroft.lib.swdd import get_relevant_tenancies
from pycroft.model import session
from pycroft.model.facilities import Room
from pycroft.model.session import with_transaction
from pycroft.model.user import (
    BaseUser,
    User,
    PreMember,
    RoomHistoryEntry,
)

from ._old import (
    user_send_mail,
)
from .edit import (
    edit_birthdate,
    edit_name,
    edit_email,
    edit_person_id,
)
from .exc import (
    LoginTakenException,
    EmailTakenException,
    UserExistsException,
    UserExistsInRoomException,
    NoTenancyForRoomException,
    MoveInDateInvalidException,
)
from .lifecycle import (
    create_user,
    login_available,
    move_in,
    move,
)
from .mail import (
    send_confirmation_email,
)
from .user_id import (
    check_user_id,
    decode_type1_user_id,
    decode_type2_user_id,
    encode_type2_user_id,
)


@with_transaction
def create_member_request(
    name: str,
    email: str,
    password: str,
    login: str,
    birthdate: date,
    swdd_person_id: int | None,
    room: Room | None,
    move_in_date: date | None,
    previous_dorm: str | None,
) -> PreMember:
    check_new_user_data(
        login,
        email,
        name,
        swdd_person_id,
        room,
        move_in_date,
    )
    if previous_dorm is None:
        check_new_user_data_unused(login=login, email=email, swdd_person_id=swdd_person_id)

    if swdd_person_id is not None and room is not None:
        tenancies = get_relevant_tenancies(swdd_person_id)

        rooms = [tenancy.room for tenancy in tenancies]

        if room not in rooms:
            raise NoTenancyForRoomException

    mr = PreMember(
        name=name,
        email=email,
        swdd_person_id=swdd_person_id,
        password=password,
        room=room,
        login=login,
        move_in_date=move_in_date,
        birthdate=birthdate,
        registered_at=session.utcnow(),
        previous_dorm=previous_dorm,
    )

    session.session.add(mr)
    session.session.flush()

    # Send confirmation mail
    send_confirmation_email(mr)

    return mr


@with_transaction
def finish_member_request(
    prm: PreMember, processor: User | None, ignore_similar_name: bool = False
) -> User:
    if prm.room is None:
        raise ValueError("Room is None")

    utcnow = session.utcnow()

    if prm.move_in_date is not None and prm.move_in_date < utcnow.date():
        prm.move_in_date = utcnow.date()

    check_new_user_data(
        prm.login,
        prm.email,
        prm.name,
        prm.swdd_person_id,
        prm.room,
        prm.move_in_date,
        ignore_similar_name,
    )

    user = user_from_pre_member(prm, processor=processor)
    processor = processor or user
    assert processor is not None

    move_in_datetime = utc.with_min_time(prm.move_in_date)
    move_in(
        user,
        prm.room.building_id,
        prm.room.level,
        prm.room.number,
        None,
        processor,
        when=move_in_datetime,
    )

    if move_in_datetime > utcnow:
        make_member_of(user, config.pre_member_group, processor, closed(utcnow, None))

    session.session.delete(prm)

    return user


def user_from_pre_member(pre_member: PreMember, processor: User) -> User:
    user, _ = create_user(
        pre_member.name,
        pre_member.login,
        pre_member.email,
        pre_member.birthdate,
        groups=[],
        processor=processor,
        address=pre_member.room.address,
        passwd_hash=pre_member.passwd_hash,
    )

    processor = processor if processor is not None else user

    user.swdd_person_id = pre_member.swdd_person_id
    user.email_confirmed = pre_member.email_confirmed

    message = deferred_gettext("Created from registration {}.").format(str(pre_member.id)).to_json()
    log_user_event(message, processor, user)

    return user


def get_member_requests() -> list[PreMember]:
    prms = (
        PreMember.q.order_by(PreMember.email_confirmed.desc())
        .order_by(PreMember.registered_at.asc())
        .all()
    )

    return prms


@with_transaction
def delete_member_request(
    prm: PreMember, reason: str | None, processor: User, inform_user: bool = True
) -> None:

    if reason is None:
        reason = "Keine Begründung angegeben."

    log_event(
        deferred_gettext("Deleted member request {}. Reason: {}").format(prm.id, reason).to_json(),
        processor,
    )

    if inform_user:
        user_send_mail(prm, MemberRequestDeniedTemplate(reason=reason), soft_fail=True)

    session.session.delete(prm)


@with_transaction
def merge_member_request(
    user: User,
    prm: PreMember,
    merge_name: bool,
    merge_email: bool,
    merge_person_id: bool,
    merge_room: bool,
    merge_password: bool,
    merge_birthdate: bool,
    processor: User,
) -> None:
    if prm.move_in_date is not None and prm.move_in_date < session.utcnow().date():
        prm.move_in_date = session.utcnow().date()

    if merge_name:
        user = edit_name(user, prm.name, processor)

    if merge_email:
        user = edit_email(
            user, prm.email, user.email_forwarded, processor, is_confirmed=prm.email_confirmed
        )

    if merge_person_id:
        user = edit_person_id(user, prm.swdd_person_id, processor)

    move_in_datetime = utc.with_min_time(prm.move_in_date)

    if merge_room:
        if prm.room:
            if user.room:
                move(
                    user,
                    prm.room.building_id,
                    prm.room.level,
                    prm.room.number,
                    processor=processor,
                    when=move_in_datetime,
                )

                if not user.member_of(config.member_group):
                    make_member_of(
                        user, config.member_group, processor, closed(move_in_datetime, None)
                    )

                    if move_in_datetime > session.utcnow():
                        make_member_of(
                            user,
                            config.pre_member_group,
                            processor,
                            closed(session.utcnow(), move_in_datetime),
                        )
            else:
                move_in(
                    user,
                    prm.room.building_id,
                    prm.room.level,
                    prm.room.number,
                    mac=None,
                    processor=processor,
                    when=move_in_datetime,
                )

                if move_in_datetime > session.utcnow():
                    make_member_of(
                        user, config.pre_member_group, processor, closed(session.utcnow(), None)
                    )

    if merge_birthdate:
        user = edit_birthdate(user, prm.birthdate, processor)

    log_msg = "Merged information from registration {}."

    if merge_password:
        user.passwd_hash = prm.passwd_hash

        log_msg += " Password overridden."
    else:
        log_msg += " Kept old password."

    log_user_event(
        deferred_gettext(log_msg).format(encode_type2_user_id(prm.id)).to_json(), processor, user
    )

    session.session.delete(prm)


def get_possible_existing_users_for_pre_member(prm: PreMember) -> set[User]:
    user_swdd_person_id = get_user_by_swdd_person_id(prm.swdd_person_id)
    user_login = User.q.filter_by(login=prm.login).first()
    user_email = User.q.filter(func.lower(User.email) == prm.email.lower()).first()

    users_name = User.q.filter_by(name=prm.name).all()
    users_similar = get_similar_users_in_room(prm.name, prm.room, 0.5)

    users = {
        user
        for user in [user_swdd_person_id, user_login, user_email] + users_name + users_similar
        if user is not None
    }

    return users


def check_new_user_data(
    login: str,
    email: str,
    name: str,
    swdd_person_id: int | None,
    room: Room | None,
    move_in_date: date | None,
    ignore_similar_name: bool = False,
) -> None:
    if room is not None and not ignore_similar_name:
        check_similar_user_in_room(name, room)

    if move_in_date is not None:
        utcnow = session.utcnow()
        if not utcnow.date() <= move_in_date <= (utcnow + timedelta(days=180)).date():
            raise MoveInDateInvalidException


def check_new_user_data_unused(login: str, email: str, swdd_person_id: int) -> None:
    """Check whether some user data from a member request is already used.

    :raises UserExistsException:
    :raises LoginTakenException:
    :raises EmailTakenException:
    """
    user_swdd_person_id = get_user_by_swdd_person_id(swdd_person_id)
    if user_swdd_person_id:
        raise UserExistsException

    if not login_available(login, session=session.session):
        raise LoginTakenException

    user_email = User.q.filter_by(email=email).first()
    if user_email is not None:
        raise EmailTakenException

    return


def get_similar_users_in_room(name: str, room: Room, ratio: float = 0.75) -> list[User]:
    """Get inhabitants of a room with a name similar to the given name.

    Eagerloading hints:
    - `room.users`
    """

    if room is None:
        return []

    return [user for user in room.users if SequenceMatcher(None, name, user.name).ratio() > ratio]


def check_similar_user_in_room(name: str, room: Room) -> None:
    """
    Raise an error if an user with a 75% name match already exists in the room
    """

    if get_similar_users_in_room(name, room):
        raise UserExistsInRoomException


def get_user_by_swdd_person_id(swdd_person_id: int | None) -> User | None:
    if swdd_person_id is None:
        return None

    return t.cast(User | None, User.q.filter_by(swdd_person_id=swdd_person_id).first())


def get_name_from_first_last(first_name: str, last_name: str) -> str:
    return f"{first_name} {last_name}" if last_name else first_name


def get_user_by_id_or_login(ident: str, email: str) -> User | None:
    re_uid1 = r"^\d{4,6}-\d{1}$"
    re_uid2 = r"^\d{4,6}-\d{2}$"

    user = User.q.filter(func.lower(User.email) == email.lower())

    if re.match(re_uid1, ident):
        if not check_user_id(ident):
            return None
        user_id, _ = decode_type1_user_id(ident)
        user = user.filter_by(id=user_id)
    elif re.match(re_uid2, ident):
        if not check_user_id(ident):
            return None
        user_id, _ = decode_type2_user_id(ident)
        user = user.filter_by(id=user_id)
    elif re.match(BaseUser.login_regex, ident):
        user = user.filter_by(login=ident)
    else:
        return None

    return t.cast(User | None, user.one_or_none())


def find_similar_users(name: str, room: Room, ratio: float) -> t.Iterable[User]:
    """Given a potential user's name and a room, find users of similar name living in that room.

    :param name: The potential user's name
    :param room: the room whose inhabitants to search
    :param ratio: the threshold which determines which matches are included in this list.
      For that, the `difflib.SequenceMatcher.ratio` must be greater than the given value.
    """
    relevant_users_q = (
        session.session.query(User).join(RoomHistoryEntry).filter(RoomHistoryEntry.room == room)
    )
    return [u for u in relevant_users_q if are_names_similar(name, u.name, threshold=ratio)]


def are_names_similar(one: str, other: str, threshold: float) -> bool:
    return SequenceMatcher(a=one, b=other).ratio() > threshold
