from flask.ext.wtf.form import Form
from wtforms.fields import TextField, PasswordField

class LoginForm(Form):
    login = TextField()
    password = PasswordField()