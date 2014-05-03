from web.form.widgets import DatePickerWidget, LazyLoadSelectWidget, \
    BootstrapFormControlDecorator, BootstrapHorizontalDecorator, \
    BootstrapFormGroupDecorator, decorate
from wtforms import TextField
from wtforms import fields
import wtforms.widgets
import datetime


class DatePickerField(fields.DateField):
    """This is a Datepicker field using bootstrap-datepicker.

    It has two additional optional arguments:
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
    widget = decorate(
        wtforms.widgets.TextInput(),
        BootstrapFormControlDecorator,
        BootstrapHorizontalDecorator,
        BootstrapFormGroupDecorator
    )

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

    def process_formdata(self, valuelist):
        try:
            super(DatePickerField, self).process_formdata(valuelist)
        except ValueError:
            if not sum(map(len, valuelist)):
                return


class LazyLoadSelectField(fields.SelectField):
    """This is a select field that loads data lazy if a dependency changes

    Its used for example for the room selection:
    The levels are loaded if you select a dormitory. The room numbers are
    loaded for the selected dormitory and level.

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
            dormitory_id = request.args.get('dormitory', 0, type=int)
            [...]
            return jsonify(dict(items=[entry.level for entry in levels]))

    The get arguments has the same name as the id of the dependency.

    As widget the LazyLoadSelectWidget is used. It renders everything
    automatically. You need only the form.js and the initializing js code:
        <script type="text/javascript" src="{{ url_for("static", filename="custom/js/form.js") }}"></script>
        <script type="text/javascript">
            $('[data-role=lazyloadselect]').lazyLoadSelect()
        </script>

    :param conditions: The names of the fields this one depends on as a List.
    :param data_endpoint: The name of the endpoint that provides the data.
    """

    widget = decorate(
        LazyLoadSelectWidget(),
        BootstrapFormControlDecorator,
        BootstrapHorizontalDecorator,
        BootstrapFormGroupDecorator
    )

    def __init__(self, *args, **kwargs):
        self.conditions = kwargs.pop("conditions")
        self.data_endpoint = kwargs.pop("data_endpoint")

        super(LazyLoadSelectField,self).__init__(*args, **kwargs)

    def pre_validate(self, form):
        pass



class ReadonlyTextField(TextField):
    def __call__(self, **kwargs):
        return self.widget(self, disabled=True )