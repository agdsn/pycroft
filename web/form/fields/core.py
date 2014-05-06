__author__ = 'shreyder'

import wtforms.fields
import wtforms.ext.sqlalchemy.fields

from ..widgets import decorate_field, BootstrapFormControlDecorator, \
    BootstrapHorizontalDecorator, BootstrapFormGroupDecorator, \
    BootstrapRadioDecorator, BootstrapHorizontalWithoutLabelDecorator, \
    BootstrapCheckboxDecorator, BootstrapFieldListWidget, \
    BootstrapFormFieldWidget


class SelectField(wtforms.fields.SelectField):
    widget = decorate_field(
        wtforms.fields.SelectField,
        BootstrapFormControlDecorator,
        BootstrapHorizontalDecorator,
        BootstrapFormGroupDecorator
    )


class SelectMultipleField(wtforms.fields.SelectMultipleField):
    widget = decorate_field(
        wtforms.fields.SelectMultipleField,
        BootstrapFormControlDecorator,
        BootstrapHorizontalDecorator,
        BootstrapFormGroupDecorator
    )


class RadioField(wtforms.fields.RadioField):
    widget = decorate_field(
        wtforms.fields.RadioField,
        BootstrapRadioDecorator,
        BootstrapHorizontalWithoutLabelDecorator,
        BootstrapFormGroupDecorator
    )


class StringField(wtforms.fields.StringField):
    widget = decorate_field(
        wtforms.fields.StringField,
        BootstrapFormControlDecorator,
        BootstrapHorizontalDecorator,
        BootstrapFormGroupDecorator
    )


class TextField(StringField):
    pass


class IntegerField(wtforms.fields.IntegerField):
    widget = decorate_field(
        wtforms.fields.IntegerField,
        BootstrapFormControlDecorator,
        BootstrapHorizontalDecorator,
        BootstrapFormGroupDecorator
    )


class DecimalField(wtforms.fields.DecimalField):
    widget = decorate_field(
        wtforms.fields.DecimalField,
        BootstrapFormControlDecorator,
        BootstrapHorizontalDecorator,
        BootstrapFormGroupDecorator
    )


class FloatField(wtforms.fields.FloatField):
    widget = decorate_field(
        wtforms.fields.FloatField,
        BootstrapFormControlDecorator,
        BootstrapHorizontalDecorator,
        BootstrapFormGroupDecorator
    )


class BooleanField(wtforms.fields.BooleanField):
    widget = decorate_field(
        wtforms.fields.BooleanField,
        BootstrapCheckboxDecorator,
        BootstrapHorizontalWithoutLabelDecorator,
        BootstrapFormGroupDecorator
    )


class DateTimeField(wtforms.fields.DateTimeField):
    widget = decorate_field(
        wtforms.fields.DateTimeField,
        BootstrapFormControlDecorator,
        BootstrapHorizontalDecorator,
        BootstrapFormGroupDecorator
    )


class DateField(wtforms.fields.DateField):
    widget = decorate_field(
        wtforms.fields.DateField,
        BootstrapFormControlDecorator,
        BootstrapHorizontalDecorator,
        BootstrapFormGroupDecorator
    )


class TextAreaField(wtforms.fields.TextAreaField):
    widget = decorate_field(
        wtforms.fields.TextAreaField,
        BootstrapFormControlDecorator,
        BootstrapHorizontalDecorator,
        BootstrapFormGroupDecorator
    )


class PasswordField(wtforms.fields.PasswordField):
    widget = decorate_field(
        wtforms.fields.PasswordField,
        BootstrapFormControlDecorator,
        BootstrapHorizontalDecorator,
        BootstrapFormGroupDecorator
    )


class FileField(wtforms.fields.FileField):
    widget = decorate_field(
        wtforms.fields.FileField,
        BootstrapHorizontalDecorator,
        BootstrapFormGroupDecorator
    )


# wtforms.fields.HiddenField is not decorated
from wtforms.fields import HiddenField


class SubmitField(wtforms.fields.SubmitField):
    widget = decorate_field(
        wtforms.fields.SubmitField,
        BootstrapFormGroupDecorator
    )


class QuerySelectField(wtforms.ext.sqlalchemy.fields.QuerySelectField):
    widget = decorate_field(
        wtforms.ext.sqlalchemy.fields.QuerySelectField,
        BootstrapFormControlDecorator,
        BootstrapHorizontalDecorator,
        BootstrapFormGroupDecorator
    )


class QuerySelectMultipleField(
    wtforms.ext.sqlalchemy.fields.QuerySelectMultipleField
):
    widget = decorate_field(
        wtforms.ext.sqlalchemy.fields.QuerySelectMultipleField,
        BootstrapFormControlDecorator,
        BootstrapHorizontalDecorator,
        BootstrapFormGroupDecorator
    )


class FieldList(wtforms.fields.FieldList):
    widget = BootstrapFieldListWidget()


class FormField(wtforms.fields.FormField):
    widget = BootstrapFormFieldWidget()
