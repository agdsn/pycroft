# -*- coding: utf-8 -*-


from flaskext.wtf import Form, TextField
from wtforms.validators import Required, Regexp

class TrafficGroupForm(Form):
    name = TextField(u"Gruppenname",[Required(message=u"Name?")])
    traffic_limit = TextField(u"Traffic Limit (GB)",
                        [Required(message=u"Wie viel GB?"),
                        Regexp(regex=u"[0-9]+",
                        message=u"Muss eine natürliche Zahl sein!")])


class PropertyGroupForm(Form):
    name = TextField(u"Gruppenname",[Required(message=u"Name?")])
