import typing

from wtforms import Form
from wtforms_widgets.fields.core import BooleanField

from pycroft.model.facilities import Room


def iter_prefixed_field_names(cls: type[Form], prefix: str) -> typing.Iterator[str]:
    return (f for f in cls.__dict__
            if hasattr(f, '_formfield') and f.startswith(prefix))


def refill_room_data(form, room):
    if room:
        form.building.data = room.building

        levels = Room.q.filter_by(building_id=room.building.id).order_by(Room.level)\
                       .distinct()

        form.level.choices = [(entry.level, str(entry.level)) for entry in
                              levels]
        form.level.data = room.level

        rooms = Room.q.filter_by(
            building_id=room.building.id,
            level=room.level
        ).order_by(Room.number).distinct()

        form.room_number.choices = [(entry.number, str(entry.number))
                                    for entry in rooms]
        form.room_number.data = room.number


def confirmable_div(confirm_field_id: str | None, prefix: str = 'form-group-') -> str:
    """Return an opening div tag linking this error div to a confirm field.

    See `confirmable-error.ts`.
    """
    attrs = ['', 'data-role="confirmable-error"',
             f'data-confirmed-by-checkbox-id="{confirm_field_id}"'] \
        if confirm_field_id else []

    return f"<div{' '.join(attrs)}>"


class ConfirmCheckboxField(BooleanField):
    """A checkbox field with data-role=confirm-checkbox.

    See `confirmable-error.ts`
    """
    def __init__(self, label=None, validators=None, false_values=None, **kwargs):
        kwargs.setdefault('render_kw', {})
        kwargs.setdefault('default', False)
        kwargs['render_kw'].setdefault('data-role', 'confirm-checkbox')
        super().__init__(label, validators, false_values, **kwargs)
