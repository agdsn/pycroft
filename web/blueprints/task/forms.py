#  Copyright (c) 2021. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details

from wtforms.validators import Optional
from wtforms_widgets.base_form import BaseForm
from wtforms_widgets.fields.core import DateField, TimeField

from pycroft.helpers.utc import combine_or_midnight, DateTimeTz


class RescheduleTaskForm(BaseForm):
    when = DateField("Neues Datum")
    when_time = TimeField("Genaue Zeit", [Optional()],
                          description="Optional. In UTC angeben.",
                          render_kw={'placeholder': 'hh:mm'})

    @property
    def full_datetime(self) -> DateTimeTz:
        return combine_or_midnight(self.when.data, self.when_time.data)
