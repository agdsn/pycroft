from flask_wtf import FlaskForm as Form
from wtforms.validators import Optional
from wtforms_widgets.fields.core import TextField, SelectMultipleField
from wtforms_widgets.fields.custom import MacField
from wtforms_widgets.fields.validators import MacAddress

from web.blueprints.facilities.forms import SelectRoomForm
from web.blueprints.helpers.host import UniqueMac
from web.form.widgets import UserIDField


class HostForm(SelectRoomForm):
    owner_id = UserIDField("Besitzer-ID")
    name = TextField("Name", validators=[Optional()],
                     description="z.B. TP-LINK WR841, FritzBox 4040 oder MacBook")

    _order = ("name", "owner_id")


class InterfaceForm(Form):
    name = TextField("Name",
                     description="z.B. eth0, en0 oder enp0s29u1u1u5",
                     validators=[Optional()])
    mac = MacField("MAC", [MacAddress(message="MAC ist ungültig!"), UniqueMac(annex_field=None)])
    ips = SelectMultipleField("IPs", validators=[Optional()])
