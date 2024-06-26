"""
pycroft.lib.mail
~~~~~~~~~~~~~~~~
"""
import logging
import os
import smtplib
import ssl
import traceback
import typing as t
from dataclasses import dataclass
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import make_msgid, formatdate

import jinja2

from pycroft.lib.exc import PycroftLibException

mail_envelope_from = os.environ.get('PYCROFT_MAIL_ENVELOPE_FROM')
mail_from = os.environ.get('PYCROFT_MAIL_FROM')
mail_reply_to = os.environ.get('PYCROFT_MAIL_REPLY_TO')
smtp_host = os.environ.get('PYCROFT_SMTP_HOST')
smtp_port = int(os.environ.get('PYCROFT_SMTP_PORT', 465))
smtp_user = os.environ.get('PYCROFT_SMTP_USER')
smtp_password = os.environ.get('PYCROFT_SMTP_PASSWORD')
smtp_ssl = os.environ.get('PYCROFT_SMTP_SSL', 'ssl')
template_path_type = os.environ.get('PYCROFT_TEMPLATE_PATH_TYPE', 'filesystem')
template_path = os.environ.get('PYCROFT_TEMPLATE_PATH', 'pycroft/templates')

logger = logging.getLogger('mail')
logger.setLevel(logging.INFO)

template_loader: jinja2.BaseLoader
if template_path_type == 'filesystem':
    template_loader = jinja2.FileSystemLoader(searchpath=f'{template_path}/mail')
else:
    template_loader = jinja2.PackageLoader(package_name='pycroft',
                                           package_path=f'{template_path}/mail')

template_env = jinja2.Environment(loader=template_loader)


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
        plain = template_env.get_template(self.template).render(mode='plain', **self.args, **kwargs)
        html = template_env.get_template(self.template).render(mode='html', **self.args, **kwargs)

        return plain, html


def compose_mail(mail: Mail) -> MIMEMultipart:
    msg = MIMEMultipart('alternative', _charset='utf-8')
    msg['Message-Id'] = make_msgid()
    msg['From'] = mail_from
    msg['To'] = Header(mail.to_address)
    msg['Subject'] = mail.subject
    msg['Date'] = formatdate(localtime=True)

    msg.attach(MIMEText(mail.body_plain, 'plain', _charset='utf-8'))

    if mail.body_html is not None:
        msg.attach(MIMEText(mail.body_html, 'html', _charset='utf-8'))

    if mail.reply_to is not None or mail.reply_to is not None:
        msg['Reply-To'] = mail_reply_to if mail.reply_to is None else mail.reply_to

    print(msg)

    return msg


class RetryableException(PycroftLibException):
    pass


def send_mails(mails: list[Mail]) -> tuple[bool, int]:
    """Send MIME text mails

    Returns False, if sending fails.  Else returns True.

    :param mails: A list of mails

    :returns: Whether the transmission succeeded
    """

    if not smtp_host:
        logger.critical("No mailserver config available")

        raise RuntimeError

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
                mime_mail = compose_mail(mail)
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
