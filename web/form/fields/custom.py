# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from web.form.widgets import LazyLoadSelectWidget,\
    BootstrapFormControlDecorator, BootstrapStandardDecorator, \
    BootstrapFormGroupDecorator, decorate, BootstrapStaticFieldWidget, \
    decorators, decorate_field, Disabler
from wtforms import TextField, StringField
from wtforms import fields
from wtforms.validators import ValidationError


def static(field):
    widget = field.kwargs.get("widget", field.field_class.widget)
    field.kwargs["widget"] = decorate(
        BootstrapStaticFieldWidget(),
        *reversed(list(decorators(widget)))
    )
    return field


def disabled(field):
    widget = field.kwargs.get("widget", field.field_class.widget)
    field.kwargs["widget"] = Disabler(widget)
    return field


class LazyLoadSelectField(fields.SelectField):
    """This is a select field that loads data lazy if a dependency changes

    Its used for example for the room selection:
    The levels are loaded if you select a building. The room numbers are
    loaded for the selected building and level.

    It needs a data endpoint that provides a json object with at least one
    element: "items". This stores a list of items. The item can be either a
    simple string - then the value of the generated <option> element is the
    same as its label or a array of two elements: [value, label].

    The request is a get xhr request sending the dependency values as url
    arguments. A sample implementation can be:

        @bp.route('/json/levels')
        def json_levels():
            if not request.is_xhr:
                abort(404)
            building_id = request.args.get('building', 0, type=int)
            [...]
            return jsonify(dict(items=[entry.level for entry in levels]))

    The get arguments has the same name as the id of the dependency.

    As widget the LazyLoadSelectWidget is used. It renders everything
    automatically. You need only the form.js and the initializing js code:
        {{ resources.link_script_file('js/form.js') }}
        <script type="text/javascript">
            $('[data-role=lazy-load-select]').lazyLoadSelect()
        </script>

    :param conditions: The names of the fields this one depends on as a List.
    :param data_endpoint: The name of the endpoint that provides the data.
    """

    widget = decorate(
        LazyLoadSelectWidget(),
        BootstrapFormControlDecorator,
        BootstrapStandardDecorator,
        BootstrapFormGroupDecorator
    )

    def __init__(self, *args, **kwargs):
        self.conditions = kwargs.pop("conditions")
        self.data_endpoint = kwargs.pop("data_endpoint")

        super(LazyLoadSelectField, self).__init__(*args, **kwargs)

    def pre_validate(self, form):
        pass


class TypeaheadField(StringField):
    """A Twitter typeahead.js field."""

    widget = decorate_field(
        StringField,
        BootstrapFormControlDecorator,
        BootstrapStandardDecorator,
        BootstrapFormGroupDecorator
    )


class ReadonlyTextField(TextField):
    def __call__(self, **kwargs):
        return self.widget(self, disabled=True)


def expected_interval_format(units):
    return ' '.join("{{}} {unit}".format(unit=unit) for unit in units)


def default_interval_format(units):
    return ' '.join("0 {unit}".format(unit=unit) for unit in units)


def rebuild_string(values, units):
    return ' '.join("{} {}".format(v, u) for v, u in zip(values, units))


class IntervalField(TextField):
    """A IntervalField """

    widget = decorate_field(
        StringField,
        BootstrapFormControlDecorator,
        BootstrapStandardDecorator,
        BootstrapFormGroupDecorator
    )

    def __init__(self, *args, **kwargs):
        super(IntervalField, self).__init__(*args, **kwargs)
        kwargs.setdefault('validators', None)
        self.expected_units = ['years', 'mons', 'days', 'hours', 'mins', 'secs']

    def __call__(self, **kwargs):
        if self.data is None:
            self.data = default_interval_format(self.expected_units)
        return super(IntervalField, self).__call__(
            class_='pycroft-interval-picker',
            autocomplete='off',
            **kwargs
        )

    def pre_validate(self, form):
        expected_format = expected_interval_format(self.expected_units)
        generic_error = ValidationError("Expected format: {}".format(expected_format))

        tokens = [x for x in self.data.split(' ') if x]
        values = tokens[::2]
        units = tokens[1::2]
        if not len(values) == len(units) == len(self.expected_units):
            raise generic_error

        if units != self.expected_units:
            units = self.expected_units
            self.data = rebuild_string(values, units)
            raise ValidationError(u'Format der Eingabe wurde korrigiert. Bitte prüfen.')

        try:
            decoded_values = [int(val) for val in values]
        except ValueError:
            raise ValidationError(u'Die Werte müssen als natürliche Zahlen angegeben werden.')

        if all(val == 0 for val in decoded_values):
            raise ValidationError("Intervalle müssen nichtleer und >0s sein.")
