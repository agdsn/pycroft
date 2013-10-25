from flask.ext.wtf.form import Form
from wtforms import TextField, PasswordField

class LoginForm(Form):
    login = TextField()
    password = PasswordField()