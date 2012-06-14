# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from web.form.widgets import DatePickerWidget
from wtforms import fields


class DatePickerField(fields.DateField):
    """This is a Datepicker field using bootstrap-datepicker.

    It has two additional optional arguments:
    :param with_today_button: If set to True a button will be rendered
                              behind the field to set the value to "today".
                              The default is false.
    :param today_title: The title of the today button. Default is "Set today!"

    I needs the datepicker css and js files!  You must also activate the
    datepicker for the widget with a js snipped:
        <script type="text/javascript">
            $('[data-role=datepicker]').datepicker();
        </script>

    To use the Today Button You also need this:
        <script type="text/javascript">
            $('[data-role=today-btn]').on("click", function (ev) {
                var $this = $(this),
                    $target = $("#" + $this.data("target")),
                    format = $target.data("datepicker").format;
                ev.preventDefault();
                $target.val(formatDate(new Date(), format));
                $target.data("datepicker").update()
            })
        </script>
    """
    widget = None
    def __init__(self, *args, **kwargs):
        if "with_today_button" in kwargs:
            self.with_today_button = kwargs.pop("with_today_button")
        else:
            self.with_today_button = False

        if "today_title" in kwargs:
            self.today_title = kwargs.pop("today_title")
        else:
            self.today_title = u"Set today!"

        super(DatePickerField, self).__init__(*args, **kwargs)

        if self.widget is None:
            self.widget = DatePickerWidget(date_format=self._format_to_widget(),
                                           with_today_button=self.with_today_button,
                                           today_title=self.today_title)

    def _format_to_widget(self):
        date_format = unicode(self.format)
        date_format = date_format.replace(u"%Y", u"yyyy")
        date_format = date_format.replace(u"%m", u"mm")
        date_format = date_format.replace(u"%d", u"dd")
        return date_format
