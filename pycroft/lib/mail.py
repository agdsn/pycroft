"""
pycroft.lib.mail
~~~~~~~~~~~~~~~~
"""

from __future__ import annotations
import logging
import os
import smtplib
import ssl
import traceback
import typing as t
from contextvars import ContextVar
from dataclasses import dataclass, field, InitVar
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import make_msgid, formatdate
from functools import lru_cache

import jinja2
from werkzeug.local import LocalProxy

from pycroft.lib.exc import PycroftLibException


# TODO proxy and DI; set at app init
_config_var: ContextVar[MailConfig] = ContextVar("config")
config: MailConfig = LocalProxy(_config_var)  # type: ignore[assignment]

logger = logging.getLogger('mail')
logger.setLevel(logging.INFO)


@dataclass
class Mail:
    to_name: str
    to_address: str
    subject: str
    body_plain: str
    body_html: str | None = None
    reply_to: str | None = None


class MailTemplate:
    template: str
    subject: str
    args: dict

    def __init__(self, **kwargs: t.Any) -> None:
        self.args = kwargs

    def render(self, **kwargs: t.Any) -> tuple[str, str]:
        plain = self.jinja_template.render(mode="plain", **self.args, **kwargs)
        html = self.jinja_template.render(mode="html", **self.args, **kwargs)

        return plain, html

    @property
    def jinja_template(self) -> jinja2.Template:
        return _get_template(self.template)


@lru_cache(maxsize=None)
def _get_template(template_location: str) -> jinja2.Template:
    if config is None:
        raise RuntimeError("`mail.config` not set up!")
    return config.template_env.get_template(template_location)


def compose_mail(mail: Mail, from_: str, default_reply_to: str | None) -> MIMEMultipart:
    msg = MIMEMultipart("alternative", _charset="utf-8")
    msg["Message-Id"] = make_msgid()
    msg["From"] = from_
    msg["To"] = str(Header(mail.to_address))
    msg["Subject"] = mail.subject
    msg["Date"] = formatdate(localtime=True)

    msg.attach(MIMEText(mail.body_plain, 'plain', _charset='utf-8'))

    if mail.body_html is not None:
        msg.attach(MIMEText(mail.body_html, 'html', _charset='utf-8'))

    if reply_to := mail.reply_to or default_reply_to:
        msg["Reply-To"] = reply_to

    print(msg)

    return msg


class RetryableException(PycroftLibException):
    pass


def send_mails(mails: list[Mail]) -> tuple[bool, int]:
    """Send MIME text mails

    Returns False, if sending fails.  Else returns True.

    :param mails: A list of mails

    :returns: Whether the transmission succeeded
    :context: config
    """
    if config is None:
        raise RuntimeError("`mail.config` not set up!")

    mail_envelope_from = config.mail_envelope_from
    mail_from = config.mail_from
    mail_reply_to = config.mail_reply_to
    smtp_host = config.smtp_host
    smtp_port = config.smtp_port
    smtp_user = config.smtp_user
    smtp_password = config.smtp_password
    smtp_ssl = config.smtp_ssl

    use_ssl = smtp_ssl == 'ssl'
    use_starttls = smtp_ssl == 'starttls'
    ssl_context = None

    if use_ssl or use_starttls:
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.verify_mode = ssl.VerifyMode.CERT_REQUIRED
            ssl_context.check_hostname = True
        except ssl.SSLError as e:
            # smtp.connect failed to connect
            logger.critical('Unable to create ssl context', extra={
                'trace': True,
                'data': {'exception_arguments': e.args}
            })
            raise RetryableException from e

    try:
        smtp: smtplib.SMTP
        if use_ssl:
            assert ssl_context is not None
            smtp = smtplib.SMTP_SSL(host=smtp_host, port=smtp_port,
                                    context=ssl_context)
        else:
            smtp = smtplib.SMTP(host=smtp_host, port=smtp_port)

        if use_starttls:
            smtp.starttls(context=ssl_context)

        if smtp_user:
            assert smtp_password is not None
            smtp.login(smtp_user, smtp_password)
    except (OSError, smtplib.SMTPException) as e:
        traceback.print_exc()

        # smtp.connect failed to connect
        logger.critical(
            "Unable to connect to SMTP server: %s",
            e,
            extra={
                "trace": True,
                "tags": {"mailserver": f"{smtp_host}:{smtp_host}"},
                "data": {"exception_arguments": e.args},
            },
        )

        raise RetryableException from e
    else:
        failures: int = 0

        for mail in mails:
            try:
                mime_mail = compose_mail(mail, from_=mail_from, default_reply_to=mail_reply_to)
                assert mail_envelope_from is not None
                smtp.sendmail(from_addr=mail_envelope_from, to_addrs=mail.to_address,
                              msg=mime_mail.as_string())
            except smtplib.SMTPException as e:
                traceback.print_exc()
                logger.critical(
                    'Unable to send mail: "%s" to "%s": %s', mail.subject, mail.to_address, e,
                    extra={
                        'trace': True,
                        'tags': {'mailserver': f"{smtp_host}:{smtp_host}"},
                        'data': {'exception_arguments': e.args, 'to': mail.to_address,
                                 'subject': mail.subject}
                    }
                )
                failures += 1

        smtp.close()

        logger.info('Tried to send mails (%i/%i succeeded)', len(mails) - failures, len(mails), extra={
            'tags': {'mailserver': f"{smtp_host}:{smtp_host}"}
        })

        return failures == 0, failures


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


@dataclass
class MailConfig:
    mail_envelope_from: str
    mail_from: str
    mail_reply_to: str | None
    smtp_host: str
    smtp_user: str
    smtp_password: str
    smtp_port: int = field(default=465)
    smtp_ssl: str = field(default="ssl")

    template_path_type: InitVar[str | None] = None
    template_path: InitVar[str | None] = None
    template_env: jinja2.Environment = field(init=False)

    @classmethod
    def from_env(cls) -> t.Self:
        env = os.environ
        config = cls(
            mail_envelope_from=env["PYCROFT_MAIL_ENVELOPE_FROM"],
            mail_from=env["PYCROFT_MAIL_FROM"],
            mail_reply_to=env.get("PYCROFT_MAIL_REPLY_TO"),
            smtp_host=env["PYCROFT_SMTP_HOST"],
            smtp_user=env["PYCROFT_SMTP_USER"],
            smtp_password=env["PYCROFT_SMTP_PASSWORD"],
            template_path_type=env.get("PYCROFT_TEMPLATE_PATH_TYPE"),
            template_path=env.get("PYCROFT_TEMPLATE_PATH"),
        )
        if (smtp_port := env.get("PYCROFT_SMTP_PORT")) is not None:
            config.smtp_port = int(smtp_port)
        if (smtp_ssl := env.get("PYCROFT_SMTP_SSL")) is not None:
            config.smtp_ssl = smtp_ssl

        return config

    def __post_init__(self, template_path_type: str | None, template_path: str | None) -> None:
        template_loader: jinja2.BaseLoader
        if template_path_type is None:
            template_path_type = "filesystem"
        if template_path is None:
            template_path = "pycroft/templates"

        if template_path_type == "filesystem":
            template_loader = jinja2.FileSystemLoader(searchpath=f"{template_path}/mail")
        else:
            template_loader = jinja2.PackageLoader(
                package_name="pycroft", package_path=f"{template_path}/mail"
            )

        self.template_env = jinja2.Environment(loader=template_loader)
