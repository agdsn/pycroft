"""
pycroft.lib.mail
~~~~~~~~~~~~~~~~
"""

from __future__ import annotations
import typing as t


from .concepts import Mail, MailTemplate
from .config import MailConfig, config
from .submission import send_mails, RetryableException
from .templates import (
    UserConfirmEmailTemplate,
    UserResetPasswordTemplate,
    UserMovedInTemplate,
    UserCreatedTemplate,
    MemberRequestPendingTemplate,
    MemberRequestDeniedTemplate,
    MemberRequestMergedTemplate,
    TaskFailedTemplate,
    MemberNegativeBalance,
)


def send_template_mails(
    email_addresses: list[str], template: MailTemplate, **kwargs: t.Any
) -> None:
    mails = []

    for addr in email_addresses:
        body_plain, body_html = template.render(**kwargs)

        mail = Mail(to_name='',
                    to_address=addr,
                    subject=template.subject,
                    body_plain=body_plain,
                    body_html=body_html)
        mails.append(mail)

    from pycroft.task import send_mails_async

    send_mails_async.delay(mails)
