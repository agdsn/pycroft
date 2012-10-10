# -*- coding: utf-8 -*-


from flask.ext.wtf import Form, TextField
from wtforms.validators import Required, Regexp
from pycroft.model.ports import Port
from web.form.fields import ReadonlyTextField

class SwitchPortForm(Form):
    name = TextField(u"Port Name",
                        [Required(message=u"Name?"),
                         Regexp(regex=Port.name_regex,
                             message=u"Richtig ist z.B. A2")])


class CNameRecordEditForm(Form):
    name = TextField(u"Alias Name", [Required(message=u"Alias?")])
    alias_for = ReadonlyTextField(u"für")