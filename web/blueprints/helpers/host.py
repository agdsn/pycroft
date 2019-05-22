import re

from flask import url_for
from wtforms.widgets import HTMLString

from pycroft.helpers.net import mac_regex
from pycroft.model.host import Interface


def validate_unique_mac(form, field):
    if re.match(mac_regex, field.data):
        interface_existing = Interface.q.filter_by(mac=field.data).first()

        if interface_existing is not None and (not hasattr(form, 'annex') or not form.annex.data):
            owner = interface_existing.host.owner

            return HTMLString("MAC bereits in Verwendung!<br/>Nutzer: " +
                              "<a target=\"_blank\" href=\"" +
                              url_for("user.user_show", user_id=owner.id) +
                              "#hosts\">" + owner.name + "</a>")
