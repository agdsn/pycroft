import re

from flask import url_for
from markupsafe import Markup
from wtforms import Form, Field, ValidationError

from pycroft.helpers.net import mac_regex
from pycroft.lib.host import get_conflicting_interface
from pycroft.model import session
from .form import confirmable_div


class UniqueMac:

    """Validates whether the mac is unique.

    :param annex_field: the name of the “I want to annex that host/interface” checkbox
    """

    def __init__(self, annex_field: str | None = 'annex'):
        self.annex_field = annex_field

    def annex_set(self, form: Form) -> bool:
        return bool(self.annex_field and getattr(form, self.annex_field).data)

    def __call__(self, form: Form, field: Field) -> None:
        if not re.match(mac_regex, field.data):
            return
        if self.annex_set(form):
            return

        current_mac = getattr(form.meta, "current_mac", None)
        ci = get_conflicting_interface(session.session, field.data, current_mac)
        if ci is None:
            return

        owner = ci.host.owner
        url = url_for("user.user_show", user_id=owner.id, _anchor="hosts")
        raise ValidationError(
            Markup(
                f"{confirmable_div(self.annex_field)}MAC bereits in Verwendung!<br/>Nutzer: "
                f'<a target="_blank" href="{url}#hosts">{owner.name}</a></div>'
            )
        )
