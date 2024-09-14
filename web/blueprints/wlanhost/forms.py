#  Copyright (c) 2024. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details

from flask_wtf import FlaskForm as Form
from wtforms.validators import Optional
from wtforms_widgets.fields.core import TextField, SelectMultipleField
from wtforms_widgets.fields.custom import MacField
from wtforms_widgets.fields.validators import MacAddress

from web.blueprints.facilities.forms import SelectRoomForm
from web.blueprints.helpers.host import UniqueMac
from web.form.widgets import UserIDField



class WLANInterfaceForm(Form):
    name = TextField("Name", validators=[Optional()])

    mac = MacField("MAC", [MacAddress(message="MAC ist ungültig!")], UniqueMac(annex_field=None))
