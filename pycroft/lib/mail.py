import logging
import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.utils import make_msgid, formatdate
from typing import List

import jinja2

from pycroft.helpers import AutoNumber

mail_envelope_from = os.environ.get('PYCROFT_MAIL_ENVELOPE_FROM')
mail_from = os.environ.get('PYCROFT_MAIL_FROM')
mail_reply_to = os.environ.get('PYCROFT_MAIL_REPLY_TO')
smtp_host = os.environ.get('PYCROFT_SMTP_HOST')
smtp_port = os.environ.get('PYCROFT_SMTP_PORT', 465)
smtp_user = os.environ.get('PYCROFT_SMTP_USER')
smtp_password = os.environ.get('PYCROFT_SMTP_PASSWORD')
smtp_ssl = os.environ.get('PYCROFT_SMTP_SSL', 'ssl')

logger = logging.getLogger('mail')

template_loader = jinja2.FileSystemLoader(searchpath="../templates/mail/")
template_env = jinja2.Environment(loader=template_loader)


class Mail:
    to: str
    subject: str
    body: str
    reply_to: str

    def __init__(self, to: str, subject: str, body: str, reply_to: str = None):
        self.to = to
        self.subject = subject
        self.body = body
        self.reply_to = reply_to


class MailTemplate:
    template: str
    subject: str
    args: dict

    def __init__(self, **kwargs):
        self.args = kwargs

    def render(self, **kwargs) -> str:
        return template_env.get_template(self.template).render(**self.args, **kwargs)


class UserConfirmEmailTemplate(MailTemplate):
    template = "user_confirm_email.html"
    subject = "Bitte bestätige deine E-Mail Adresse // Please confirm your email address"


def compose_mail(mail: Mail) -> MIMEText:
    mime_mail = MIMEText(mail.body, _subtype='html', _charset='utf-8')

    mime_mail['Message-Id'] = make_msgid()
    mime_mail['From'] = mail_from
    mime_mail['To'] = mail.to
    mime_mail['Subject'] = mail.subject
    mime_mail['Date'] = formatdate(localtime=True)

    if mail.reply_to is not None or mail.reply_to is not None:
        mime_mail['Reply-To'] = mail_reply_to if mail.reply_to is None else mail.reply_to

    return mime_mail


def send_mails(mails: List[Mail]) -> (bool, int):
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
            return False

    try:
        if use_ssl:
            smtp = smtplib.SMTP_SSL(host=smtp_host, port=smtp_port,
                                    context=ssl_context)
        else:
            smtp = smtplib.SMTP(host=smtp_host, port=smtp_port)

        if use_starttls:
            smtp.starttls(context=ssl_context)

        if smtp_user:
            smtp.login(smtp_user, smtp_password)

        failures: int = 0

        for mail in mails:
            try:
                mime_mail = compose_mail(mail)
                smtp.sendmail(from_addr=mail_envelope_from, to_addrs=mail.to,
                              msg=mime_mail.as_string())
            except smtplib.SMTPException as e:
                logger.critical('Unable to send mail', extra={
                    'trace': True,
                    'tags': {'mailserver': f"{smtp_host}:{smtp_host}"},
                    'data': {'exception_arguments': e.args, 'to': mail.to, 'subject': mail.subject}
                })

                failures += 1

        smtp.close()
    except IOError as e:
        # smtp.connect failed to connect
        logger.critical('Unable to connect to SMTP server', extra={
            'trace': True,
            'tags': {'mailserver': f"{smtp_host}:{smtp_host}"},
            'data': {'exception_arguments': e.args}
        })
        return False
    else:
        logger.info('Tried to sent mails', extra={
            'tags': {'mailserver': f"{smtp_host}:{smtp_host}"},
            'data': {'total': len(mails), 'failures': failures}
        })
        return failures == 0, failures
