# -*- coding: utf-8 -*-


from flask.ext.wtf import Form, TextField
from wtforms.validators import Required, Regexp
from pycroft.model.ports import Port

class SwitchPortForm(Form):
    name = TextField(u"Port Name",
                        [Required(message=u"Name?"),
                         Regexp(regex=Port.name_regex,
                             message=u"Richtig ist z.B. A2")])

