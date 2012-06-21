from web.form.widgets import DatePickerWidget, LazyLoadSelectWidget
from wtforms import fields


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


class LazyLoadSelectField(fields.SelectField):
    widget = LazyLoadSelectWidget()

    def __init__(self, *args, **kwargs):
        self.conditions = kwargs.pop("conditions")
        self.data_endpoint = kwargs.pop("data_endpoint")

        super(LazyLoadSelectField,self).__init__(*args, **kwargs)

    def pre_validate(self, form):
        pass
