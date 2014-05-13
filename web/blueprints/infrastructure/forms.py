# -*- coding: utf-8 -*-


from flask.ext.wtf import Form
from wtforms.validators import Required, Regexp
from pycroft.model.dns import ARecord
from pycroft.model.port import Port
from web.form.fields.core import TextField, SelectField, QuerySelectField
from web.form.fields.custom import ReadonlyTextField


def a_records_query(host_id):
    return ARecord.q.filter(
        ARecord.host_id == host_id
    ).order_by(ARecord.id)


class SwitchPortForm(Form):
    name = TextField(u"Port Name",
        [Required(message=u"Name?"),
         Regexp(regex=Port.name_regex,
             message=u"Richtig ist z.B. A2")])


class CNameRecordEditForm(Form):
    name = TextField(u"Alias Name", [Required(message=u"Alias?")])
    record_for = ReadonlyTextField(u"für")


class RecordCreateForm(Form):
    type = SelectField(u"Type",
        choices=[('a_record', 'ARecord'), ('aaaa_record', 'AAAARecord'),
                 ('cname_record', 'CNameRecord'), ('mx_record', 'MXRecord'),
                 ('ns_record', 'NSRecord'), ('srv_record', 'SRVRecord')])


class CNameRecordCreateForm(Form):
    name = TextField(u"Alias Name", [Required(message=u"Alias?")])
    record_for = QuerySelectField(u"für", get_label='name')
