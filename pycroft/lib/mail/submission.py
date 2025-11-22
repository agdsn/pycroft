import logging
import smtplib
import ssl
import traceback

from pycroft.lib.exc import PycroftLibException
from .concepts import Mail
from .config import config


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



class RetryableException(PycroftLibException):
    pass

