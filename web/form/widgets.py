# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from wtforms import widgets
from wtforms.widgets.core import html_params


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
            html = u'<div class="input-append">'
            html += field_html
            html += u'<a href="#" title="%s" class="btn" data-role="today-btn" data-target="%s"><i class="icon-retweet"></i></a>' % (self.today_title, field.id)
            html += u'</div>'
            return html
        else:
            return field_html


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
