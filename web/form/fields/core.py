# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import datetime
from itertools import chain
import re

import wtforms.fields
import wtforms.ext.sqlalchemy.fields
from pycroft._compat import iteritems, iterkeys
from pycroft.model import session

from ..widgets import decorate_field, BootstrapFormControlDecorator, \
    BootstrapStandardDecorator, BootstrapFormGroupDecorator, \
    BootstrapRadioDecorator, BootstrapCheckboxDecorator, \
    BootstrapFieldListWidget, BootstrapFormFieldWidget, \
    BootstrapDatepickerWidget, MoneyFieldDecorator, decorate


class SelectField(wtforms.fields.SelectField):
    widget = decorate_field(
        wtforms.fields.SelectField,
        BootstrapFormControlDecorator,
        BootstrapStandardDecorator,
        BootstrapFormGroupDecorator
    )


class SelectMultipleField(wtforms.fields.SelectMultipleField):
    widget = decorate_field(
        wtforms.fields.SelectMultipleField,
        BootstrapFormControlDecorator,
        BootstrapStandardDecorator,
        BootstrapFormGroupDecorator
    )


class RadioField(wtforms.fields.RadioField):
    widget = BootstrapFieldListWidget()
    option_widget = decorate(
        wtforms.widgets.RadioInput(),
        BootstrapRadioDecorator,
        BootstrapFormGroupDecorator
    )


class StringField(wtforms.fields.StringField):
    widget = decorate_field(
        wtforms.fields.StringField,
        BootstrapFormControlDecorator,
        BootstrapStandardDecorator,
        BootstrapFormGroupDecorator
    )


class TextField(StringField):
    pass


class IntegerField(wtforms.fields.IntegerField):
    widget = decorate_field(
        wtforms.fields.IntegerField,
        BootstrapFormControlDecorator,
        BootstrapStandardDecorator,
        BootstrapFormGroupDecorator
    )


class DecimalField(wtforms.fields.DecimalField):
    widget = decorate_field(
        wtforms.fields.DecimalField,
        BootstrapFormControlDecorator,
        BootstrapStandardDecorator,
        BootstrapFormGroupDecorator
    )


class MoneyField(wtforms.fields.DecimalField):
    widget = decorate_field(
        wtforms.fields.DecimalField,
        MoneyFieldDecorator,
        BootstrapFormControlDecorator,
        BootstrapStandardDecorator,
        BootstrapFormGroupDecorator
    )

    def process_formdata(self, valuelist):
        if valuelist:
            valuelist[0] = valuelist[0].replace(",", ".")
        return super(MoneyField, self).process_formdata(valuelist)


class FloatField(wtforms.fields.FloatField):
    widget = decorate_field(
        wtforms.fields.FloatField,
        BootstrapFormControlDecorator,
        BootstrapStandardDecorator,
        BootstrapFormGroupDecorator
    )


class BooleanField(wtforms.fields.BooleanField):
    widget = decorate_field(
        wtforms.fields.BooleanField,
        BootstrapCheckboxDecorator,
        BootstrapFormGroupDecorator
    )


class DateTimeField(wtforms.fields.DateTimeField):
    widget = decorate(
        BootstrapDatepickerWidget(),
        BootstrapFormControlDecorator,
        BootstrapStandardDecorator,
        BootstrapFormGroupDecorator
    )


class DateField(wtforms.fields.DateField):
    widget = decorate(
        BootstrapDatepickerWidget(),
        BootstrapFormControlDecorator,
        BootstrapStandardDecorator,
        BootstrapFormGroupDecorator
    )
    supported_directives = {
        'd': 'dd',
        'm': 'mm',
        'a': 'D',
        'A': 'DD',
        'b': 'M',
        'B': 'MM',
        'y': 'yy',
        'Y': 'yyyy',
    }
    unsupported_directives = set(iter("wHIPMSfzZjUWcxX"))
    format_string_pattern = re.compile(r"(%+)([^%]|$)", re.M)
    # Set literals are only supported in Python 2.7 or higher
    available_datepicker_options = {
        "autoclose", "before_show_day", "calendar_weeks", "clear_btn",
        "days_of_week_disabled", "end_date", "force_parse", "format",
        "keyboard_navigation", "language", "min_view_mode", "multidate",
        "multidate_separator", "orientation", "start_date", "start_view",
        "today_btn", "today_highlight", "week_start"
    }

    def __init__(self, label=None, validators=None, format='%Y-%m-%d',
                 **kwargs):
        # Move Bootstrap datepicker specific options to its own dict
        self.datepicker_options = dict((
            (option, value) for (option, value) in iteritems(kwargs)
            if option in self.available_datepicker_options
        ))
        for option in iterkeys(self.datepicker_options):
            kwargs.pop(option)
        defaults = {'default': session.utcnow(), 'language': 'de',
                    'today_highlight': 'true', 'today_btn': 'linked'}
        self.datepicker_options = dict(chain(
            iteritems(defaults), iteritems(self.datepicker_options)))
        # The format option is used by both DateField and Bootstrap datepicker,
        # albeit with a different format string syntax.
        self.datepicker_options['format'] = self.convert_format_string(format)
        super(DateField, self).__init__(label, validators, format, **kwargs)

    @classmethod
    def _replacement_function(cls, match):
        percentage_signs = match.group(1)
        percentage_sign_count = len(percentage_signs)
        directive = match.group(2)
        # Even number of percentage signs => all percentages are escaped
        if percentage_sign_count % 2 == 0:
            replacement = directive
        elif directive in cls.supported_directives:
            replacement = cls.supported_directives[directive]
        elif directive in cls.unsupported_directives:
            message = "Format directive %{} not supported by " \
                      "Bootstrap datepicker.".format(directive)
            raise ValueError(message)
        else:
            message = "Unknown format directive: %{}".format(directive)
            raise ValueError(message)
        return percentage_signs[0:percentage_sign_count//2] + replacement

    @classmethod
    def convert_format_string(cls, format):
        """
        Convert a datetime strftime/strptime to a Bootstrap datepicker format
        string.
        """
        return cls.format_string_pattern.sub(cls._replacement_function, format)


class TextAreaField(wtforms.fields.TextAreaField):
    widget = decorate_field(
        wtforms.fields.TextAreaField,
        BootstrapFormControlDecorator,
        BootstrapStandardDecorator,
        BootstrapFormGroupDecorator
    )


class PasswordField(wtforms.fields.PasswordField):
    widget = decorate_field(
        wtforms.fields.PasswordField,
        BootstrapFormControlDecorator,
        BootstrapStandardDecorator,
        BootstrapFormGroupDecorator
    )


class FileField(wtforms.fields.FileField):
    widget = decorate_field(
        wtforms.fields.FileField,
        BootstrapStandardDecorator,
        BootstrapFormGroupDecorator
    )


# No need to decorate wtforms.fields.HiddenField
HiddenField = wtforms.fields.HiddenField


class SubmitField(wtforms.fields.SubmitField):
    widget = decorate_field(
        wtforms.fields.SubmitField,
        BootstrapFormGroupDecorator
    )


class QuerySelectField(
    wtforms.ext.sqlalchemy.fields.QuerySelectField
):
    widget = decorate_field(
        wtforms.ext.sqlalchemy.fields.QuerySelectField,
        BootstrapFormControlDecorator,
        BootstrapStandardDecorator,
        BootstrapFormGroupDecorator
    )


class QuerySelectMultipleField(
    wtforms.ext.sqlalchemy.fields.QuerySelectMultipleField
):
    widget = decorate_field(
        wtforms.ext.sqlalchemy.fields.QuerySelectMultipleField,
        BootstrapFormControlDecorator,
        BootstrapStandardDecorator,
        BootstrapFormGroupDecorator
    )


class FieldList(wtforms.fields.FieldList):
    widget = BootstrapFieldListWidget()


class FormField(wtforms.fields.FormField):
    widget = BootstrapFormFieldWidget()
