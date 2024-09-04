import os
import typing as t

from sqlalchemy import select, ScalarResult
from sqlalchemy.orm import Session

from pycroft.helpers.user import generate_random_str
from pycroft.lib.mail import (
    MailTemplate,
    Mail,
    UserConfirmEmailTemplate,
    MemberRequestMergedTemplate,
)
from pycroft.model import session
from pycroft.model.session import with_transaction
from pycroft.model.user import (
    User,
    PreMember,
    BaseUser,
    PropertyGroup,
    Membership,
)
from pycroft.task import send_mails_async

from .user_id import (
    encode_type2_user_id,
)

mail_confirm_url = os.getenv("MAIL_CONFIRM_URL")


def format_user_mail(user: User, text: str) -> str:
    return text.format(
        name=user.name,
        login=user.login,
        id=encode_type2_user_id(user.id),
        email=user.email if user.email else "-",
        email_internal=user.email_internal,
        room_short=user.room.short_name if user.room_id is not None else "-",
        swdd_person_id=user.swdd_person_id if user.swdd_person_id else "-",
    )


def user_send_mails(
    users: t.Iterable[BaseUser],
    template: MailTemplate | None = None,
    soft_fail: bool = False,
    use_internal: bool = True,
    body_plain: str = None,
    subject: str = None,
    **kwargs: t.Any,
) -> None:
    """
    Send a mail to a list of users

    :param users: Users who should receive the mail
    :param template: The template that should be used. Can be None if body_plain is supplied.
    :param soft_fail: Do not raise an exception if a user does not have an email and use_internal
        is set to True
    :param use_internal: If internal mail addresses can be used (@agdsn.me)
        (Set to False to only send to external mail addresses)
    :param body_plain: Alternative plain body if not template supplied
    :param subject:  Alternative subject if no template supplied
    :param kwargs: kwargs that will be used during rendering the template
    :return:
    """

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

    send_mails_async.delay(mails)


def user_send_mail(
    user: BaseUser,
    template: MailTemplate,
    soft_fail: bool = False,
    use_internal: bool = True,
    **kwargs: t.Any,
) -> None:
    user_send_mails([user], template, soft_fail, use_internal, **kwargs)


def get_active_users(session: Session, group: PropertyGroup) -> ScalarResult[User]:
    return session.scalars(
        select(User).join(User.current_memberships).where(Membership.group == group).distinct()
    )


def group_send_mail(group: PropertyGroup, subject: str, body_plain: str) -> None:
    users = get_active_users(session=session.session, group=group)
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
