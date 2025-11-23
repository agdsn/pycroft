import logging
import smtplib
import ssl
import traceback

from pycroft.lib.exc import PycroftLibException
from .concepts import Mail
from .config import config, SmtpSslType


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


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

    smtp = try_create_smtp(
        config.smtp_ssl, smtp_host, smtp_port, config.smtp_user, config.smtp_password
    )

    failures: int = 0

    for mail in mails:
        try:
            mime_mail = mail.compose(from_=mail_from, default_reply_to=mail_reply_to)
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


def try_create_smtp(
    smtp_ssl: SmtpSslType, smtp_host: str, smtp_port: int, smtp_user: str, smtp_password: str
) -> smtplib.SMTP:
    """
        :raises RetryableException:
    """
    try:
        smtp: smtplib.SMTP
        if smtp_ssl == "ssl":
            smtp = smtplib.SMTP_SSL(
                host=smtp_host, port=smtp_port, context=try_create_ssl_context()
            )
        else:
            smtp = smtplib.SMTP(host=smtp_host, port=smtp_port)

        if smtp_ssl == "starttls":
            smtp.starttls(context=try_create_ssl_context())

        if smtp_user:
            assert smtp_password is not None
            smtp.login(smtp_user, smtp_password)
        return smtp
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


def try_create_ssl_context() -> ssl.SSLContext:
    """
        :raises RetryableException:
    """
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
    return ssl_context


class RetryableException(PycroftLibException):
    pass

