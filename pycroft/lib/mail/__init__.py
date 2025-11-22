"""
pycroft.lib.mail
~~~~~~~~~~~~~~~~
"""

from __future__ import annotations
import typing as t


from .concepts import Mail, MailTemplate
from .config import MailConfig, config
from .submission import send_mails, RetryableException


class UserConfirmEmailTemplate(MailTemplate):
    template = "user_confirm_email.html"
    subject = "Bitte bestätige deine E-Mail Adresse // Please confirm your email address"


class UserResetPasswordTemplate(MailTemplate):
    template = "user_reset_password.html"
    subject = "Neues Passwort setzen // Set a new password"


class UserMovedInTemplate(MailTemplate):
    template = "user_moved_in.html"
    subject = "Wohnortänderung // Change of residence"


class UserCreatedTemplate(MailTemplate):
    template = "user_created.html"
    subject = "Willkommen bei der AG DSN // Welcome to the AG DSN"


class MemberRequestPendingTemplate(MailTemplate):
    template = "member_request_pending.html"
    subject = "Deine Mitgliedschaftsanfrage // Your member request"


class MemberRequestDeniedTemplate(MailTemplate):
    template = "member_request_denied.html"
    subject = "Mitgliedschaftsanfrage abgelehnt // Member request denied"


class MemberRequestMergedTemplate(MailTemplate):
    template = "member_request_merged.html"
    subject = "Mitgliedskonto zusammengeführt // Member account merged"


class TaskFailedTemplate(MailTemplate):
    template = "task_failed.html"
    subject = "Aufgabe fehlgeschlagen // Task failed"


class MemberNegativeBalance(MailTemplate):
    template = "member_negative_balance.html"
    subject =  "Deine ausstehenden Zahlungen // Your due payments"


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
