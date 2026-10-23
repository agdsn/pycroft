from wtforms.form import BaseForm
import typing as t


from wtforms import ValidationError
from wtforms_widgets.fields.core import StringField

from pycroft.model import session
from pycroft.model.user import User


class UserIDField(StringField):
    """A User-ID Field"""

    @t.override
    def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
        super().__init__(*args, **kwargs)

    def __call__(self, **kwargs: t.Any) -> t.Any:
        return super().__call__(**kwargs)

    @t.override
    def pre_validate(self, form: BaseForm) -> None:
        if self.data is None:
            raise ValidationError("Nutzer-ID nicht angegeben.")
        try:
            id = int(self.data)
        except ValueError:
            raise ValidationError("Nutzer-ID muss eine ganzzahl sein.") from None
        if session.session.get(User, id) is None:
            raise ValidationError("Ungültige Nutzer-ID.")
