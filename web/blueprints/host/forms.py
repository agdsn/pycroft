from wtforms.validators import DataRequired, Optional

from web.blueprints.facilities.forms import SelectRoomForm
from web.form.fields.core import TextField, QuerySelectField, \
    SelectMultipleField
from web.form.fields.custom import UserIDField, MacField
from flask_wtf import FlaskForm as Form

from web.form.fields.validators import MacAddress


class HostForm(SelectRoomForm):
    owner_id = UserIDField(u"Besitzer-ID")
    name = TextField(u"Name", [DataRequired(u"Der Host benötigt einen Namen!")],
                     description=u"z.B. TP-LINK WR841, FritzBox 4040 oder MacBook")

    _order = ("name", "owner_id")


class InterfaceForm(Form):
    name = TextField(u"Name",description=u"z.B. eth0, en0 oder enp0s29u1u1u5")
    mac = MacField(u"MAC", [MacAddress(message=u"MAC ist ungültig!")])
    ips = SelectMultipleField(u"IPs", validators=[Optional()])
