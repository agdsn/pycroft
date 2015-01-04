# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from wtforms.validators import Optional


class OptionalIf(Optional):
    # makes a field optional if some other data is supplied
    def __init__(self, deciding_field, *args, **kwargs):
        self.deciding_field = deciding_field
        super(OptionalIf, self).__init__(*args, **kwargs)

    def __call__(self, form, field):
        deciding_field = form._fields.get(self.deciding_field)
        if deciding_field is None:
            raise Exception('no field named "{}" in form'.format(
                self.deciding_field))
        if bool(deciding_field.data):
            super(OptionalIf, self).__call__(form, field)
