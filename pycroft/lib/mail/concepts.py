import typing as t
from dataclasses import dataclass
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import make_msgid, formatdate
from functools import lru_cache

import jinja2

from .config import config

@dataclass
class Mail:
    to_name: str
    to_address: str
    subject: str
    body_plain: str
    body_html: str | None = None
    reply_to: str | None = None

    @property
    def body_plain_mime(self) -> MIMEText:
        return MIMEText(self.body_plain, "plain", _charset="utf-8")

    @property
    def body_html_mime(self) -> MIMEText | None:
        if not self.body_html:
            return None
        return MIMEText(self.body_html, "html", _charset="utf-8")


    def compose(self, from_: str, default_reply_to: str | None) -> MIMEMultipart:
        msg = MIMEMultipart("alternative", _charset="utf-8")
        msg["Message-Id"] = make_msgid()
        msg["From"] = from_
        msg["To"] = str(Header(self.to_address))
        msg["Subject"] = self.subject
        msg["Date"] = formatdate(localtime=True)
        msg.attach(self.body_plain_mime)
        if (html := self.body_html_mime) is not None:
            msg.attach(html)
        if reply_to := self.reply_to or default_reply_to:
            msg["Reply-To"] = reply_to

        print(msg)

        return msg


class MailTemplate:
    template: str
    subject: str
    args: dict

    def __init__(self, loader: t.Callable[[str], jinja2.Template] | None = None, **kwargs: t.Any) -> None:
        self.jinja_template: jinja2.Template = (loader or _get_template)(self.template)
        self.args = kwargs

    # TODO don't put this as a method on the template… We want a separate render method for each template.
    def render(self, **kwargs: t.Any) -> tuple[str, str]:
        plain = self.jinja_template.render(mode="plain", **self.args, **kwargs)
        html = self.jinja_template.render(mode="html", **self.args, **kwargs)

        return plain, html


@lru_cache(maxsize=None)
def _get_template(template_location: str) -> jinja2.Template:
    try:
        return config.template_env.get_template(template_location)
    except RuntimeError as e:
        raise RuntimeError("`mail.config` not set up!") from e


