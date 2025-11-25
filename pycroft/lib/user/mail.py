import os
import typing as t
from datetime import date, timedelta

from sqlalchemy import select, ScalarResult
from sqlalchemy.orm import Session

from pycroft.helpers.user import generate_random_str
from pycroft.lib.mail import (
    MailTemplate,
    Mail,
)
from pycroft.lib.mail.templates import (
    MemberRequestMergedTemplate,
    MoveOutReminder,
    UserConfirmEmailTemplate,
    UserResetPasswordTemplate,
)
from pycroft.model import session
from pycroft.model.session import with_transaction
from pycroft.model.user import (
    User,
    PreMember,
    BaseUser,
    Membership,
    PropertyGroup,
)
from pycroft.model.facilities import Building, Room
from pycroft.task import send_mails_async

from .user_id import (
    encode_type2_user_id,
)

mail_confirm_url = os.getenv("MAIL_CONFIRM_URL")
password_reset_url = os.getenv("PASSWORD_RESET_URL")


def format_user_mail(user: User, text: str) -> str:
    return text.format(
        name=user.name,
        login=user.login,
        id=encode_type2_user_id(user.id),
        email=user.email if user.email else "-",
        email_internal=user.email_internal,
        room_short=user.room.short_name if user.room is not None else "-",
        swdd_person_id=user.swdd_person_id if user.swdd_person_id else "-",
    )


def user_send_mails(
    users: t.Iterable[BaseUser],
    template: MailTemplate | None = None,
    soft_fail: bool = False,
    use_internal: bool = True,
    body_plain: str | None = None,
    subject: str | None = None,
    send_mails: t.Callable[[list[Mail]], None] | None = None,
    **kwargs: t.Any,
) -> None:
    """
    Send a mail to a list of users

    :param users: Users who should receive the mail
    :param template: The template that should be used. Can be None if body_plain is supplied.
        if supplied, must take a `user` parameter.
    :param soft_fail: Do not raise an exception if a user does not have an email and use_internal
        is set to True
    :param use_internal: If internal mail addresses can be used (@agdsn.me)
        (Set to False to only send to external mail addresses)
    :param body_plain: Alternative plain body if not template supplied
    :param subject:  Alternative subject if no template supplied
    :param kwargs: kwargs that will be used during rendering the template
    :return:
    """

    assert (template is not None) ^ (body_plain is not None), \
        "user_send_mails should be called with either template or plain body"
    assert (body_plain is not None) == (subject is not None), \
        "subject must be passed if and only if body is passed"

    mails = []

    for user in users:
        if isinstance(user, User) and all(
            (use_internal, not (user.email_forwarded and user.email), user.has_property("mail"))
        ):
            # Use internal email
            email = user.email_internal
        elif user.email:
            # Use external email
            email = user.email
        else:
            if soft_fail:
                return
            else:
                raise ValueError("No contact email address available.")

        if template is not None:
            # Template given, render...
            plaintext, html = template.render(
                user=user, user_id=encode_type2_user_id(user.id), **kwargs
            )
            subject = template.subject
        else:
            # No template given, use formatted body_mail instead.
            if not isinstance(user, User):
                raise ValueError("Plaintext email not supported for other User types.")
            if body_plain is None:
                raise ValueError("Must use either template or body_plain")

            html = None
            plaintext = format_user_mail(user, body_plain)

        if plaintext is None or subject is None:
            raise ValueError("No plain body supplied.")

        mail = Mail(
            to_name=user.name,
            to_address=email,
            subject=subject,
            body_plain=plaintext,
            body_html=html,
        )
        mails.append(mail)

    (send_mails or send_mails_async.delay)(mails)


def user_send_mail(
    user: BaseUser,
    template: MailTemplate,
    soft_fail: bool = False,
    use_internal: bool = True,
    **kwargs: t.Any,
) -> None:
    user_send_mails([user], template, soft_fail, use_internal, **kwargs)


def get_active_users_with_building(
    session: Session, groups: t.List[PropertyGroup], buildings: t.List[Building]
) -> ScalarResult[User]:

    statement = select(User)

    if groups:
        group_ids: t.List[int] = [g.id for g in groups]
        statement = (
            statement.join(User.current_memberships)
            .where(Membership.group_id.in_(group_ids))
            .distinct()
        )
    # if building is not None, we add the filter to the query
    if buildings:
        building_ids: t.List[int] = [b.id for b in buildings]
        statement = (
            statement.join(User.room).join(Room.building).where(Building.id.in_(building_ids))
        )

    return session.scalars(statement)


def group_send_mail(
    groups: t.List[PropertyGroup], subject: str, body_plain: str, buildings: t.List[Building]
) -> None:
    users = get_active_users_with_building(
        session=session.session, groups=groups, buildings=buildings
    )
    user_send_mails(users, soft_fail=True, body_plain=body_plain, subject=subject)


def send_member_request_merged_email(
    user: PreMember, merged_to: User, password_merged: bool
) -> None:
    user_send_mail(
        user,
        MemberRequestMergedTemplate(
            merged_to=merged_to,
            merged_to_user_id=encode_type2_user_id(merged_to.id),
            password_merged=password_merged,
        ),
    )


@with_transaction
def send_confirmation_email(user: BaseUser) -> None:
    user.email_confirmed = False
    user.email_confirmation_key = generate_random_str(64)

    if not mail_confirm_url:
        raise ValueError("No url specified in MAIL_CONFIRM_URL")

    user_send_mail(
        user,
        UserConfirmEmailTemplate(
            email_confirm_url=mail_confirm_url.format(user.email_confirmation_key)
        ),
    )


def send_password_reset_mail(user: User) -> bool:
    user.password_reset_token = generate_random_str(64)

    if not password_reset_url:
        raise ValueError("No url specified in PASSWORD_RESET_URL")

    try:
        user_send_mail(
            user,
            UserResetPasswordTemplate(
                password_reset_url=password_reset_url.format(user.password_reset_token)
            ),
            use_internal=False,
        )
    except ValueError:
        user.password_reset_token = None
        return False

    return True


def mail_soon_to_move_out_members(session: Session, send_mails: t.Callable[[list[Mail]], None]):
    """Dependency-free implementation of the celery task of the same name."""
    contract_end = contract_end_reminder_date(session)
    user_send_mails(
        get_members_with_contract_end_at(session, contract_end),
        template=MoveOutReminder(),
        contract_end=contract_end,
        send_mails=send_mails,
    )


# TODO move to pycroft.lib.user or somwhere else suitable
def get_members_with_contract_end_at(session: Session, date: date):
    # TODO implement
    pass


# TODO move to pycroft.lib.user or somwhere else suitable
def contract_end_reminder_date(session: Session):
    return date.today() + timedelta(days=7)

