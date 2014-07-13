# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from itertools import imap

from flask import url_for
from markupsafe import escape, Markup
import wtforms.ext.sqlalchemy.fields
import wtforms.fields
from wtforms.widgets.core import html_params, HTMLString

from web.templates import page_resources


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


class BootstrapStandardDecorator(WidgetDecorator):
    """
    Renders a field in horizontal layout.

    Horizontal layout is a two column layout, where the label is placed in the
    left column and the field is placed right next to it.
    """
    def render_horizontal(self, field, **kwargs):
        return HTMLString(u''.join([
            u'<div class="col-sm-5">',
            field.label(class_=u'control-label'),
            u'</div>',
            u'<div class="col-sm-7">',
            self.widget(field, **kwargs),
            u'</div>',
        ]))

    def render_inline(self, field, **kwargs):
        return HTMLString(u''.join([
            field.label(class_=u'sr-only'),
            self.widget(field, placeholder=field.label.text, **kwargs),
        ]))

    def render_basic(self, field, **kwargs):
        return HTMLString(u''.join([
            field.label(),
            self.widget(field, **kwargs),
        ]))

    def __call__(self, field, **kwargs):
        render_mode = kwargs.pop("render_mode", "basic")
        if render_mode == "basic":
            return self.render_basic(field, **kwargs)
        elif render_mode == "horizontal":
            return self.render_horizontal(field, **kwargs)
        elif render_mode == "inline":
            return self.render_inline(field, **kwargs)
        else:
            raise ValueError("Unknown render mode: {0}".format(render_mode))


class BootstrapRadioCheckboxDecorator(WidgetDecorator):
    """
    Renders a field in horizontal layout.

    Horizontal layout is a two column layout, where the label is placed in the
    left column and the field is placed right next to it.
    """
    wrapper_class = None

    def _render(self, field, **kwargs):
        return HTMLString(u''.join([
            u'<div class="',
            self.wrapper_class,
            u'">',
            field.label(
                u"{0} {1}".format(
                    self.widget(field, **kwargs),
                    escape(field.label.text)
                )),
            u'</div>',
        ]))

    def render_basic(self, field, **kwargs):
        return self._render(field, **kwargs)

    def render_horizontal(self, field, **kwargs):
        return HTMLString(u''.join([
            u'<div class="col-sm-offset-5 col-sm-7">',
            self._render(field, **kwargs),
            u'</div>',
        ]))

    def render_inline(self, field, **kwargs):
        return field.label(u"{0} {1}".format(
            self.widget(field, **kwargs),
            escape(field.label.text)
        ), class_=self.wrapper_class + "-inline")

    def __call__(self, field, **kwargs):
        render_mode = kwargs.pop("render_mode", "horizontal")
        if render_mode == "basic":
            return self.render_basic(field, **kwargs)
        elif render_mode == "horizontal":
            return self.render_horizontal(field, **kwargs)
        elif render_mode == "inline":
            return self.render_inline(field, **kwargs)
        else:
            raise ValueError("Unknown render mode: {0}".format(render_mode))


class BootstrapRadioDecorator(BootstrapRadioCheckboxDecorator):
    wrapper_class = u"radio"


class BootstrapCheckboxDecorator(BootstrapRadioCheckboxDecorator):
    wrapper_class = u"checkbox"


class BootstrapFieldListWidget(object):
    def __call__(self, field, **kwargs):
        return HTMLString(u''.join(imap(lambda f: f(**kwargs), field)))


class BootstrapFormFieldWidget(object):
    def __call__(self, field, **kwargs):
        return HTMLString(u''.join(imap(lambda f: f(**kwargs), field)))


class BootstrapStaticFieldWidget(object):
    """Render a static Bootstrap control."""
    def __call__(self, field, **kwargs):
        kwargs["class_"] = u"form-control-static"
        # Assume that the field provides access to its value.
        value = field._value()
        return HTMLString(u''.join([
            u'<p {}>'.format(html_params(**kwargs)),
            value,
            u'</p>',
        ]))


def decorators(widget):
    """
    Yields all decorators of a widget starting from the outermost.
    """
    while isinstance(widget, WidgetDecorator):
        yield type(widget)
        widget = widget.widget


def decorate(widget, *decorators):
    """
    Decorate a widget with a list of decorators.
    :param widget: a widget
    :param tuple[WidgetDecorator] decorators: some decorators
    :rtype: WidgetDecorator
    :returns: decorated widget
    """
    return reduce(lambda w, d: d(w), decorators, widget)


def decorate_field(field, *decorators):
    """
    Return a field's widget decorated with the given decorators..
    :param wtforms.fields.core.Field field: a WTForms field
    :param tuple[WidgetDecorator] decorators: some decorators
    :rtype: WidgetDecorator
    :returns: decorated widget
    """
    return decorate(field.widget, *decorators)


from markupsafe import Markup


class BootstrapDatepickerWidget(object):
    """Renders datetime fields using bootstrap-datepicker."""
    def __call__(self, field, **kwargs):
        kwargs["data-provide"] = u"datepicker"
        for (option, value) in field.datepicker_options.iteritems():
            attribute = 'data-date-{}'.format(option.replace('_', '-'))
            kwargs[attribute] = value
        page_resources.link_script(url_for(
            "static", filename="datepicker/js/bootstrap-datepicker.js"
        ))
        page_resources.link_script(url_for(
            "static", filename="datepicker/js/locales/bootstrap-datepicker.de.js"
        ))
        return HTMLString(u"<input {}>".format(html_params(**kwargs)))


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
