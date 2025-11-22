import os
import typing as t
from contextvars import ContextVar
from dataclasses import dataclass, field, InitVar

import jinja2
from werkzeug.local import LocalProxy

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


_config_var: ContextVar[MailConfig] = ContextVar("config")
config: MailConfig = LocalProxy(_config_var)  # type: ignore[assignment]

