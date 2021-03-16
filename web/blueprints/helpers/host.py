import re
from typing import Optional

from flask import url_for
from wtforms import Form, Field, ValidationError
from wtforms.widgets import HTMLString

from pycroft.helpers.net import mac_regex
from pycroft.model.host import Interface
from .form import confirmable_div


class UniqueMac:
    """Validates whether the mac is unique.

    :param annex_field: the name of the “I want to annex that host/interface” checkbox
    """

    def __init__(self, annex_field: Optional[str] = 'annex'):
        self.annex_field = annex_field

    def annex_set(self, form: Form) -> bool:
        return self.annex_field and getattr(form, self.annex_field).data

    @staticmethod
    def conflicting_interface(mac: str, current_mac: Optional[str] = None) -> Optional[Interface]:
        return Interface.q.filter_by(mac=mac).filter(mac != current_mac).first()

    def __call__(self, form: Form, field: Field):
        current_mac = getattr(form.meta, 'current_mac', None)

        if any((
            not re.match(mac_regex, field.data),
            self.annex_set(form),
            (conflicting_interface := self.conflicting_interface(field.data, current_mac)) is None,
        )):
            return

        owner = conflicting_interface.host.owner
        url = url_for('user.user_show', user_id=owner.id, _anchor='hosts')
        raise ValidationError(HTMLString(
            f'{confirmable_div(self.annex_field)}MAC bereits in Verwendung!<br/>Nutzer: '
            f'<a target="_blank" href="{url}#hosts">{owner.name}</a></div>'
        ))
