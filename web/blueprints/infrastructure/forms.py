from wtforms.validators import DataRequired, IPAddress

from web.blueprints.facilities.forms import SelectRoomForm
from web.form.fields.core import TextField


class PortForm(SelectRoomForm):
    switchport_name = TextField(label="Switchport Name", validators=[DataRequired()])
    patchport_name = TextField(label="→ Patchport Name", validators=[DataRequired()])

    _order = ("switchport_name", "patchport_name")


class SwitchForm(SelectRoomForm):
    name = TextField(label="Name", validators=[DataRequired()])
    management_ip = TextField(label="Management IP", validators=[DataRequired(), IPAddress()])
