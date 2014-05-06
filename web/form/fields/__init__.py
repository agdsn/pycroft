from web.form.widgets import decorate, decorators, BootstrapStaticFieldWidget

__author__ = 'shreyder'


def static(field):
    widget = field.kwargs.get("widget", field.field_class.widget)
    field.kwargs["widget"] = decorate(
        BootstrapStaticFieldWidget(),
        *reversed(list(decorators(widget)))
    )
    return field
