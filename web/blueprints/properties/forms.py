# -*- coding: utf-8 -*-


from flask.ext.wtf import Form
from wtforms.validators import DataRequired, Regexp
from web.form.fields.core import TextField

class TrafficGroupForm(Form):
    name = TextField(u"Gruppenname",[DataRequired(message=u"Name?")])
    traffic_limit = TextField(u"Traffic Limit (GB)",
                        [DataRequired(message=u"Wie viel GB?"),
                        Regexp(regex=u"[0-9]+",
                        message=u"Muss eine natürliche Zahl sein!")])


class PropertyGroupForm(Form):
    name = TextField(u"Gruppenname",[DataRequired(message=u"Name?")])
