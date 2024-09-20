import typing as t


from pycroft.lib.mail import MemberRequestPendingTemplate
from pycroft.model.session import with_transaction
from pycroft.model.user import (
    User,
    PreMember,
)

from .member_request import finish_member_request
from .mail import user_send_mail


@with_transaction
def confirm_mail_address(
    key: str,
) -> tuple[
    t.Literal["pre_member", "user"],
    t.Literal["account_created", "request_pending"] | None,
]:
    if not key:
        raise ValueError("No key given")

    mr = PreMember.q.filter_by(email_confirmation_key=key).one_or_none()
    user = User.q.filter_by(email_confirmation_key=key).one_or_none()

    if mr is None and user is None:
        raise ValueError("Unknown confirmation key")
    # else: one of {mr, user} is not None

    if user is None:
        assert mr is not None
        if mr.email_confirmed:
            raise ValueError("E-Mail already confirmed")

        mr.email_confirmed = True
        mr.email_confirmation_key = None

        reg_result: t.Literal["account_created", "request_pending"]
        if (
            mr.swdd_person_id is not None
            and mr.room is not None
            and mr.previous_dorm is None
            and mr.is_adult
        ):
            finish_member_request(mr, None)
            reg_result = "account_created"
        else:
            user_send_mail(mr, MemberRequestPendingTemplate(is_adult=mr.is_adult))
            reg_result = "request_pending"

        return "pre_member", reg_result
    elif mr is None:
        assert user is not None
        user.email_confirmed = True
        user.email_confirmation_key = None

        return "user", None
    else:
        raise RuntimeError(
            "Same mail confirmation key has been given to both a PreMember and a User"
        )
