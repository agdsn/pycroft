from flask_wtf import FlaskForm as Form
from wtforms.validators import DataRequired, IPAddress

from web.blueprints.facilities.forms import SelectRoomForm
from web.form.fields.core import TextField, QuerySelectField
from web.form.fields.filters import to_uppercase, to_lowercase


class SwitchPortForm(Form):
    name = TextField(label="Name", validators=[DataRequired()], filters=[to_uppercase])
    patch_port = QuerySelectField(label="Patch-Port", get_label="name", allow_blank=True)


class SwitchForm(SelectRoomForm):
    name = TextField(label="Name", validators=[DataRequired()], filters=[to_lowercase])
    management_ip = TextField(label="Management IP", validators=[DataRequired(), IPAddress()])
