from dataclasses import dataclass
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import make_msgid, formatdate


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
