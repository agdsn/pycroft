# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from cgi import escape
from itertools import imap

from flask import url_for

from wtforms.widgets.core import html_params, HTMLString
import wtforms.fields
import wtforms.ext.sqlalchemy.fields


class WidgetDecorator(object):
    """Decorate widgets."""

    def __init__(self, widget):
        """
        :param widget: Original widget to be decorated.
        """
        if widget is None:
            raise ValueError('Parameter widget may not be None.')
        self.widget = widget


class BootstrapFormGroupDecorator(WidgetDecorator):
    """
    Wraps a widget inside a Bootstrap form-group and prints errors.

    The widget's output is wrapped in a Bootstrap form-group. Any field errors
    are displayed in Bootstrap help-blocks after the widget.
    """
    def __call__(self, field, **kwargs):
        classes = [u'form-group']
        if field.errors:
            classes.append(u'has-error')
        html = [
            u'<div class="{0}">'.format(u' '.join(classes)),
            self.widget(field, **kwargs),
        ]
        html.extend(imap(
            lambda e: u'<p class="help-block">{0}</p>'.format(escape(e)),
            field.errors
        ))
        html.append(u'</div>')
        return HTMLString(u''.join(html))


class BootstrapFormControlDecorator(WidgetDecorator):
    """Adds the Bootstrap form-control class to a widget."""
    def __call__(self, field, **kwargs):
        if 'class_' in kwargs:
            kwargs['class_'] = u'form-control ' + kwargs['class_']
        else:
            kwargs['class_'] = u'form-control'
        return self.widget(field, **kwargs)


class BootstrapHorizontalDecorator(WidgetDecorator):
    """
    Renders a field in horizontal layout.

    Horizontal layout is a two column layout, where the label is placed in the
    left column and the field is placed right next to it.
    """
    def __call__(self, field, **kwargs):
        return HTMLString(u''.join([
            u'<div class="col-sm-5">',
            field.label(class_=u'control-label'),
            u'</div>',
            u'<div class="col-sm-7">',
            self.widget(field, **kwargs),
            u'</div>',
        ]))


class BootstrapHorizontalWithoutLabelDecorator(WidgetDecorator):
    """
    Renders a field in horizontal layout.

    Horizontal layout is a two column layout, where the label is placed in the
    left column and the field is placed right next to it.
    """
    def __call__(self, field, **kwargs):
        return HTMLString(u''.join([
            u'<div class="col-sm-offset-5 col-sm-7">',
            self.widget(field, **kwargs),
            u'</div>',
        ]))


class BootstrapRadioCheckboxDecorator(WidgetDecorator):
    """Wraps a widget with its label inside a div."""
    wrapper_class = None

    def __call__(self, field, **kwargs):
        return HTMLString(u''.join([
            u'<div class="',
            self.wrapper_class,
            u'">',
            field.label(
                u"{0} {1}".format(
                    self.widget(field, **kwargs),
                    field.label.text
                ),
                class_=u'control-label'),
            u'</div>',
        ]))


class BootstrapRadioDecorator(BootstrapRadioCheckboxDecorator):
    wrapper_class = u"radio"


class BootstrapRadioInlineDecorator(BootstrapRadioCheckboxDecorator):
    wrapper_class = u"radio-inline"


class BootstrapCheckboxDecorator(BootstrapRadioCheckboxDecorator):
    wrapper_class = u"checkbox"


class BootstrapCheckboxInlineDecorator(BootstrapRadioCheckboxDecorator):
    wrapper_class = u"checkbox-inline"


class BootstrapFieldListWidget(object):
    def __call__(self, field, **kwargs):
        return HTMLString(u''.join(imap(lambda f: f(**kwargs), field)))


class BootstrapFormFieldWidget(object):
    def __call__(self, field, **kwargs):
        return HTMLString(u''.join(imap(lambda f: f(**kwargs), field)))


def decorate(widget, *decorators):
    """Decorate a widget with a list of decorators."""
    return reduce(lambda w, d: d(w), decorators, widget)


def decorate_field(field, *decorators):
    """Replace a field's widget by  decorators and replace ."""
    field.widget = decorate(field.widget, *decorators)


def monkey_patch_wtforms():
    decorate_field(
        wtforms.fields.SelectField,
        BootstrapFormControlDecorator,
        BootstrapHorizontalDecorator,
        BootstrapFormGroupDecorator
    )
    decorate_field(
        wtforms.fields.SelectMultipleField,
        BootstrapFormControlDecorator,
        BootstrapHorizontalDecorator,
        BootstrapFormGroupDecorator
    )
    decorate_field(
        wtforms.fields.RadioField,
        BootstrapRadioDecorator,
        BootstrapHorizontalWithoutLabelDecorator,
        BootstrapFormGroupDecorator
    )
    decorate_field(
        wtforms.fields.StringField,
        BootstrapFormControlDecorator,
        BootstrapHorizontalDecorator,
        BootstrapFormGroupDecorator
    )
    decorate_field(
        wtforms.fields.IntegerField,
        BootstrapFormControlDecorator,
        BootstrapHorizontalDecorator,
        BootstrapFormGroupDecorator
    )
    decorate_field(
        wtforms.fields.DecimalField,
        BootstrapFormControlDecorator,
        BootstrapHorizontalDecorator,
        BootstrapFormGroupDecorator
    )
    decorate_field(
        wtforms.fields.FloatField,
        BootstrapFormControlDecorator,
        BootstrapHorizontalDecorator,
        BootstrapFormGroupDecorator
    )
    decorate_field(
        wtforms.fields.BooleanField,
        BootstrapRadioDecorator,
        BootstrapHorizontalWithoutLabelDecorator,
        BootstrapFormGroupDecorator
    )
    decorate_field(
        wtforms.fields.DateTimeField,
        BootstrapFormControlDecorator,
        BootstrapHorizontalDecorator,
        BootstrapFormGroupDecorator
    )
    decorate_field(
        wtforms.fields.DateField,
        BootstrapFormControlDecorator,
        BootstrapHorizontalDecorator,
        BootstrapFormGroupDecorator
    )
    decorate_field(
        wtforms.fields.TextAreaField,
        BootstrapFormControlDecorator,
        BootstrapHorizontalDecorator,
        BootstrapFormGroupDecorator
    )
    decorate_field(
        wtforms.fields.PasswordField,
        BootstrapFormControlDecorator,
        BootstrapHorizontalDecorator,
        BootstrapFormGroupDecorator
    )
    decorate_field(
        wtforms.fields.FileField,
        BootstrapHorizontalDecorator,
        BootstrapFormGroupDecorator
    )
    # wtforms.fields.HiddenField is not decorated
    decorate_field(
        wtforms.fields.SubmitField,
        BootstrapFormGroupDecorator
    )
    decorate_field(
        wtforms.ext.sqlalchemy.fields.QuerySelectField,
        BootstrapFormControlDecorator,
        BootstrapHorizontalDecorator,
        BootstrapFormGroupDecorator
    )
    decorate_field(
        wtforms.ext.sqlalchemy.fields.QuerySelectMultipleField,
        BootstrapFormControlDecorator,
        BootstrapHorizontalDecorator,
        BootstrapFormGroupDecorator
    )
    wtforms.fields.FieldList.widget = BootstrapFieldListWidget()
    wtforms.fields.FormField.widget = BootstrapFormFieldWidget()


monkey_patch_wtforms()

from markupsafe import Markup

class DatePickerWidget(wtforms.widgets.TextInput):
    """This is a Datepicker widget usinng bootstrap-datepicker.

    It has three optional arguments:
    :param date_format: The dateformat - default is yyyy-mm-dd
    :param with_today_button: If set to True a button will be rendered
                              behind the field to set the value to "today".
                              The default is false.
    :param today_title: The title of the today button. Default is "Set today!"

    It needs the datepicker css and js files!
        <link rel="stylesheet" href="{{ url_for("static", filename="datepicker/css/datepicker.css") }}">
        <script type="text/javascript" src="{{ url_for("static", filename="datepicker/js/bootstrap-datepicker.js") }}"></script>
        <script type="text/javascript" src="{{ url_for("static", filename="custom/js/form.js") }}"></script>

    You must also activate the
    datepicker for the widget with a js snipped:
        <script type="text/javascript">
            $('[data-role=datepicker]').datepicker();
        </script>

    To use the Today Button You also need this:
        <script type="text/javascript">
            $('[data-role=today-btn]').todayButton();
        </script>
    """
    # ToDo: Develop a media framework like the Django fields-media stuff

    def __init__(self, *args, **kwargs):
        if "date_format" in kwargs:
            self.date_format = kwargs.pop("date_format")
        else:
            self.date_format = u"yyyy-mm-dd"

        if "with_today_button" in kwargs:
            self.with_today_button = kwargs.pop("with_today_button")
        else:
            self.with_today_button = False

        if "today_title" in kwargs:
            self.today_title = kwargs.pop("today_title")
        else:
            self.today_title = u"Set today!"

        super(DatePickerWidget, self).__init__(*args, **kwargs)


    def __call__(self, field, **kwargs):
        kwargs['data-role'] = u'datepicker'
        kwargs['data-date-format'] = self.date_format
        field_html = super(DatePickerWidget, self).__call__(field, **kwargs)
        if self.with_today_button:
            html = u'<div class="input-group">'
            html += field_html
            html += u'<a href="#" title="%s" class="btn btn-default input-group-addon glyphicon glyphicon-retweet" data-role="today-btn" data-target="%s"></a>' % (self.today_title, field.id)
            html += u'</div>'
            return Markup(html)
        else:
            return Markup(field_html)


class CheckBoxWidget(wtforms.widgets.Select):
    """A simple multi selection widget rendered as Checkbox list.
    
    It uses the bootstrap markup.
    """
    def __call__(self, field, **kwargs):
        kwargs.setdefault('type', 'checkbox')
        field_id = kwargs.pop('id', field.id)
        html = []
        for value, label, checked in field.iter_choices():
            choice_id = u'%s-%s' % (field_id, value)
            options = dict(kwargs, name=field.name, value=value, id=choice_id)
            html.append(u'<label class="checkbox" %s>' % html_params(id=field_id))
            if checked:
                options['checked'] = 'checked'
            html.append(u'<input %s>' % html_params(**options))
            html.append(label)
            html.append(u'</label>')
        return u''.join(html)


class LazyLoadSelectWidget(wtforms.widgets.Select):
    """This is the widget for the LazyLoadSelectField

    Please look at web.form.fields.LazyLoadSelectField for more information.
    """

    def __call__(self, field, **kwargs):
        conditions = getattr(field, "conditions", None)
        if conditions is not None:
            kwargs["data-fieldids"] = ",".join(conditions)
        kwargs['data-role'] = u'lazyloadselect'
        kwargs['data-url'] = url_for(field.data_endpoint)

        return super(LazyLoadSelectWidget, self).__call__(field, **kwargs)
