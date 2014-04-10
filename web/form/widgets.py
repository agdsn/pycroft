# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from cgi import escape
import json

from flask import url_for

from wtforms import widgets
from flask.ext import wtf
from wtforms.widgets.core import html_params, HTMLString


class BootstrapHorizontalFieldWidget(object):
    """
    Renders a field in Bootstrap's horizontal layout.
    Wraps the output of an existing widget in <div> tags.
    """
    def __init__(self, widget):
        """
        :param widget: Original widget
        :return:
        """
        self.widget = widget

    def __call__(self, field, **kwargs):
        classes = [u'control-group']
        if field.errors:
            classes.append(u'error')
        html = [
            u'<div class="%s">' % u' '.join(classes),
            field.label(class_="control-label"),
            u'<div class="controls">',
            self.widget(field, **kwargs)
        ]
        if field.errors:
            html.append(u'<span class="help-inline">')
            html.append(escape(u';'.join(field.errors)))
            html.append(u'</span>')
        html.append(u'</div></div>')
        return HTMLString(u''.join(html))


class BootstrapFieldListWidget(object):
    def __call__(self, field):
        html = map(lambda f: f(), list(field))
        return HTMLString(u''.join(html))


class BootstrapFormFieldWidget(object):
    def __call__(self, field):
        html = map(lambda f: f(), list(field))
        return HTMLString(u''.join(html))


def replace_with_horizontal(field):
    field.widget = BootstrapHorizontalFieldWidget(field.widget)


# wtforms.fields.core fields
replace_with_horizontal(wtf.SelectField)
replace_with_horizontal(wtf.SelectMultipleField)
replace_with_horizontal(wtf.RadioField)
replace_with_horizontal(wtf.StringField)
replace_with_horizontal(wtf.IntegerField)
replace_with_horizontal(wtf.DecimalField)
replace_with_horizontal(wtf.FloatField,)
replace_with_horizontal(wtf.BooleanField)
replace_with_horizontal(wtf.DateTimeField)
replace_with_horizontal(wtf.DateField)
wtf.FormField.widget = BootstrapFormFieldWidget()
wtf.FieldList.widget = BootstrapFieldListWidget()
# wtforms.fields.simple fields
replace_with_horizontal(wtf.TextAreaField)
replace_with_horizontal(wtf.PasswordField)
replace_with_horizontal(wtf.FileField)
# wtf.HiddenField is omitted
replace_with_horizontal(wtf.SubmitField)
# wtforms.ext.sqlalchemy.fields
replace_with_horizontal(wtf.QuerySelectField)
replace_with_horizontal(wtf.QuerySelectMultipleField)

from markupsafe import Markup

class DatePickerWidget(widgets.TextInput):
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


class CheckBoxWidget(widgets.Select):
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


class LazyLoadSelectWidget(widgets.Select):
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
