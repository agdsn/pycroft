import wtforms_widgets
from wtforms import ValidationError

from pycroft.model.user import User


class UserIDField(wtforms_widgets.fields.core.StringField):
    """A User-ID Field """

    def __init__(self, *args, **kwargs):
        super(UserIDField, self).__init__(*args, **kwargs)

    def __call__(self, **kwargs):
        return super(UserIDField, self).__call__(
            **kwargs
        )

    def pre_validate(self, form):
        if User.q.get(self.data) is None:
            raise ValidationError("Ungültige Nutzer-ID.")
