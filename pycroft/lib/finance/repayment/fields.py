from typing import Any, Mapping

from marshmallow import fields, ValidationError
from schwifty import IBAN


class IBANField(fields.Field):
    """Field that serializes to a IBAN and deserializes
    to a string.
    """

    def _deserialize(
        self, value: Any, attr: str | None, data: Mapping[str, Any], **kwargs
    ) -> IBAN:
        try:
            return IBAN(value, validate_bban=True)
        except ValueError as error:
            raise ValidationError("Field must be a valid IBAN.") from error
