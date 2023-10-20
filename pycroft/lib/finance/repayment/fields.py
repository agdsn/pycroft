from marshmallow import fields, ValidationError
from schwifty import IBAN


class IBANField(fields.Field):
    """Field that serializes to a IBAN and deserializes
    to a string.
    """

    def _deserialize(self, value, attr, data, **kwargs) -> IBAN:
        try:
            return IBAN(value)
        except ValueError as error:
            raise ValidationError("Pin codes must contain only digits.") from error
