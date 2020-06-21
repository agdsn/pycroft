from web.form.widgets import UserIDField
from wtforms.validators import DataRequired, Optional

from web.blueprints.facilities.forms import SelectRoomForm
from wtforms_widgets.fields.core import TextField, QuerySelectField, \
    SelectMultipleField
from wtforms_widgets.fields.custom import MacField
from flask_wtf import FlaskForm as Form

from wtforms_widgets.fields.validators import MacAddress


class HostForm(SelectRoomForm):
    owner_id = UserIDField("Besitzer-ID")
    name = TextField("Name", validators=[Optional()],
                     description="z.B. TP-LINK WR841, FritzBox 4040 oder MacBook")

    _order = ("name", "owner_id")


class InterfaceForm(Form):
    name = TextField("Name",
                     description="z.B. eth0, en0 oder enp0s29u1u1u5",
                     validators=[Optional()])
    mac = MacField("MAC", [MacAddress(message="MAC ist ungültig!")])
    ips = SelectMultipleField(u"IPs", validators=[Optional()])
