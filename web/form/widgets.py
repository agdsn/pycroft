import typing as t


import wtforms_widgets
from wtforms import ValidationError, Form

from pycroft.model import session
from pycroft.model.user import User


class UserIDField(wtforms_widgets.fields.core.StringField):
    """A User-ID Field """

    def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
        super().__init__(*args, **kwargs)

    def __call__(self, **kwargs: t.Any) -> t.Any:
        return super().__call__(
            **kwargs
        )

    def pre_validate(self, form: Form) -> None:
        try:
            id = int(self.data)
        except ValueError:
            raise ValidationError("Nutzer-ID muss eine ganzzahl sein.") from None
        if session.session.get(User, id) is None:
            raise ValidationError("Ungültige Nutzer-ID.")
