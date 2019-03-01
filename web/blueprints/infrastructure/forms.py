from flask_wtf import FlaskForm as Form
from wtforms.validators import DataRequired, IPAddress

from pycroft.model.net import VLAN
from web.blueprints.facilities.forms import SelectRoomForm
from web.form.fields.core import TextField, QuerySelectField, \
    QuerySelectMultipleField
from web.form.fields.filters import to_uppercase, to_lowercase


def vlan_query():
    return VLAN.q.order_by(VLAN.vid)


class SwitchPortForm(Form):
    name = TextField(label="Name", validators=[DataRequired()], filters=[to_uppercase])
    patch_port = QuerySelectField(label="Patch-Port", get_label="name", allow_blank=True)
    default_vlans = QuerySelectMultipleField(label="Standard VLANs",
                                     get_label=lambda vlan: "{} ({})".format(vlan.name, vlan.vid),
                                     query_factory=vlan_query,
                                     allow_blank=True,
                                     render_kw={'size': 25})


class SwitchForm(SelectRoomForm):
    name = TextField(label="Name", validators=[DataRequired()], filters=[to_lowercase])
    management_ip = TextField(label="Management IP", validators=[DataRequired(), IPAddress()])
