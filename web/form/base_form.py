from collections import OrderedDict

from flask_wtf import FlaskForm as Form


class BaseForm(Form):
    def __iter__(self):
        field_order = getattr(self, '_order', [])

        if field_order:
            ordered_fields = OrderedDict()

            for name in field_order:
                ordered_fields[name] = self._fields.pop(name)

            ordered_fields.update(self._fields)

            self._fields = ordered_fields

        return super(BaseForm, self).__iter__()
