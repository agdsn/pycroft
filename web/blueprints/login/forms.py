# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from flask_wtf.form import FlaskForm as Form
from wtforms.validators import Regexp
from pycroft.model.user import User
from wtforms_widgets.fields.core import TextField, PasswordField


class LoginForm(Form):
    login = TextField()
    password = PasswordField()
