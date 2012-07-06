# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.


from flask.ext.wtf import Form, TextField
from wtforms.validators import Required, Regexp

class TrafficGroupForm(Form):
    name = TextField(u"Gruppenname",[Required(message=u"Name?")])
    traffic_limit = TextField(u"Traffic Limit (GB)",
                        [Required(message=u"Wie viel GB?"),
                        Regexp(regex=u"[0-9]+",
                        message=u"Muss eine natürliche Zahl sein!")])


class PropertyGroupForm(Form):
    name = TextField(u"Gruppenname",[Required(message=u"Name?")])
