from cgi import escape
from itertools import imap

from flask import url_for

from wtforms.widgets.core import html_params, HTMLString
import wtforms.fields
import wtforms.ext.sqlalchemy.fields


class BootstrapBaseWidget(object):
    """
    Augments existing widgets to be Bootstrap compatible.

    Horizontal layout is a two column layout, where the label is placed in the
    left column and the field is placed right next to it.
    The field is wrapped in a Bootstrap form-group. Field errors are
    displayed in Bootstrap help-blocks.
    """

    def __init__(self, widget=None):
        """
        :param widget: Original widget
        :return:
        """
        self.widget = widget

    def decorate(self, widget):
        """
        Replace a field's widget with an instance of this widget.

        The replaced widget is preserved and used to render the actual field.
        """
        self.widget = widget
        return self


class BootstrapFormGroupWidget(BootstrapBaseWidget):
    """Wraps an existing widget inside a Bootstrap form-group."""
    def __call__(self, field, **kwargs):
        classes = [u'form-group']
        if field.errors:
            classes.append(u'has-error')
        html = [
            u'<div class="%s">' % u' '.join(classes),
            self.widget(field, **kwargs),
        ]
        html.extend(imap(
            lambda e: u'<p class="help-block">{}</p>'.format(escape(e)),
            field.errors
        ))
        html.append(u'</div>')
        return HTMLString(u''.join(html))


class BootstrapFormControlWidget(BootstrapBaseWidget):
    def __call__(self, field, **kwargs):
        if kwargs.has_key('class_'):
            kwargs['class_'] = u'form-control ' + kwargs['class_']
        else:
            kwargs['class_'] = u'form-control'
        return self.widget(field, **kwargs)


class BootstrapHorizontalWidget(BootstrapBaseWidget):
    """
    Renders a field in horizontal layout.

    Horizontal layout is a two column layout, where the label is placed in the
    left column and the field is placed right next to it.
    """

    def __init__(self, widget=None):
        super(BootstrapHorizontalWidget, self).__init__(widget)

    def __call__(self, field, **kwargs):
        return HTMLString(u''.join([
            u'<div class="col-sm-2">',
            field.label(class_=u'control-label'),
            u'</div>',
            u'<div class="col-sm-3">',
            self.widget(field, **kwargs),
            u'</div>',
        ]))


class BootstrapHorizontalWithoutLabelWidget(BootstrapBaseWidget):
    """
    Renders a field in horizontal layout.

    Horizontal layout is a two column layout, where the label is placed in the
    left column and the field is placed right next to it.
    """

    def __init__(self, widget=None, omit_label=False):
        super(BootstrapHorizontalWithoutLabelWidget, self).__init__(widget)

    def __call__(self, field, **kwargs):
        return HTMLString(u''.join([
            u'<div class="col-sm-offset-2 col-sm-10">',
            self.widget(field, **kwargs),
            u'</div>',
        ]))



class BootstrapRadioCheckboxWidget(BootstrapBaseWidget):

    wrapper_class = ""

    def __init__(self, widget=None):
        super(BootstrapRadioCheckboxWidget, self).__init__(widget)

    def __call__(self, field, **kwargs):
        return HTMLString(u''.join([
            u'<div class="',
            self.wrapper_class,
            u'">',
            field.label(
                u"{} {}".format(
                    self.widget(field, **kwargs),
                    field.label.text
                ),
                class_=u'control-label'),
            u'</div>',
        ]))


class BootstrapRadioWidget(BootstrapRadioCheckboxWidget):
    wrapper_class = "radio"


class BootstrapRadioInlineWidget(BootstrapRadioCheckboxWidget):
    wrapper_class = "radio-inline"


class BootstrapCheckboxWidget(BootstrapRadioCheckboxWidget):
    wrapper_class = "checkbox"


class BootstrapCheckboxInlineWidget(BootstrapRadioCheckboxWidget):
    wrapper_class = "checkbox-inline"


class BootstrapFieldListWidget(object):
    def __call__(self, field):
        html = map(lambda f: f(), list(field))
        return HTMLString(u''.join(html))


class BootstrapFormFieldWidget(object):
    def __call__(self, field):
        html = map(lambda f: f(), list(field))
        return HTMLString(u''.join(html))


def decorate(widget, *widgets):
    return reduce(lambda w, d: d.decorate(w), widgets, widget)


def replace_with_decorations(field, *widgets):
    field.widget = decorate(field.widget, *widgets)


def monkey_patch_wtforms():
    replace_with_decorations(
        wtforms.fields.SelectField,
        BootstrapFormControlWidget(),
        BootstrapHorizontalWidget(),
        BootstrapFormGroupWidget()
    )
    replace_with_decorations(
        wtforms.fields.SelectMultipleField,
        BootstrapFormControlWidget(),
        BootstrapHorizontalWidget(),
        BootstrapFormGroupWidget()
    )
    replace_with_decorations(
        wtforms.fields.RadioField,
        BootstrapRadioWidget(),
        BootstrapHorizontalWithoutLabelWidget(),
        BootstrapFormGroupWidget()
    )
    replace_with_decorations(
        wtforms.fields.StringField,
        BootstrapFormControlWidget(),
        BootstrapHorizontalWidget(),
        BootstrapFormGroupWidget()
    )
    replace_with_decorations(
        wtforms.fields.IntegerField,
        BootstrapFormControlWidget(),
        BootstrapHorizontalWidget(),
        BootstrapFormGroupWidget()
    )
    replace_with_decorations(
        wtforms.fields.DecimalField,
        BootstrapFormControlWidget(),
        BootstrapHorizontalWidget(),
        BootstrapFormGroupWidget()
    )
    replace_with_decorations(
        wtforms.fields.FloatField,
        BootstrapFormControlWidget(),
        BootstrapHorizontalWidget(),
        BootstrapFormGroupWidget()
    )
    replace_with_decorations(
        wtforms.fields.BooleanField,
        BootstrapRadioWidget(),
        BootstrapHorizontalWithoutLabelWidget(),
        BootstrapFormGroupWidget()
    )
    replace_with_decorations(
        wtforms.fields.DateTimeField,
        BootstrapFormControlWidget(),
        BootstrapHorizontalWidget(),
        BootstrapFormGroupWidget()
    )
    replace_with_decorations(
        wtforms.fields.DateField,
        BootstrapFormControlWidget(),
        BootstrapHorizontalWidget(),
        BootstrapFormGroupWidget()
    )
    replace_with_decorations(
        wtforms.fields.TextAreaField,
        BootstrapFormControlWidget(),
        BootstrapHorizontalWidget(),
        BootstrapFormGroupWidget()
    )
    replace_with_decorations(
        wtforms.fields.PasswordField,
        BootstrapFormControlWidget(),
        BootstrapHorizontalWidget(),
        BootstrapFormGroupWidget()
    )
    replace_with_decorations(
        wtforms.fields.FileField,
        BootstrapHorizontalWidget(),
        BootstrapFormGroupWidget()
    )
    # wtforms.fields.HiddenField is not decorated
    replace_with_decorations(
        wtforms.fields.SubmitField,
        BootstrapFormGroupWidget()
    )
    replace_with_decorations(
        wtforms.ext.sqlalchemy.fields.QuerySelectField,
        BootstrapFormControlWidget(),
        BootstrapHorizontalWidget(),
        BootstrapFormGroupWidget()
    )
    replace_with_decorations(
        wtforms.ext.sqlalchemy.fields.QuerySelectMultipleField,
        BootstrapFormControlWidget(),
        BootstrapHorizontalWidget(),
        BootstrapFormGroupWidget()
    )


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
