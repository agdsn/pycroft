from _typeshed import Incomplete
from fints.types import (
    Container as Container,
    SegmentSequence as SegmentSequence,
    TypedField as TypedField,
)
from fints.utils import (
    DocTypeMixin as DocTypeMixin,
    FieldRenderFormatStringMixin as FieldRenderFormatStringMixin,
    FixedLengthMixin as FixedLengthMixin,
    Password as Password,
)

class DataElementField(DocTypeMixin, TypedField): ...
class ContainerField(TypedField): ...
class DataElementGroupField(DocTypeMixin, ContainerField): ...

class GenericField(FieldRenderFormatStringMixin, DataElementField):
    type: Incomplete

class GenericGroupField(DataElementGroupField):
    type: Incomplete

class TextField(FieldRenderFormatStringMixin, DataElementField):
    type: str

class AlphanumericField(TextField):
    type: str

class DTAUSField(DataElementField):
    type: str

class NumericField(FieldRenderFormatStringMixin, DataElementField):
    type: str

class ZeroPaddedNumericField(NumericField):
    type: str
    def __init__(self, *args, **kwargs) -> None: ...

class DigitsField(FieldRenderFormatStringMixin, DataElementField):
    type: str

class FloatField(DataElementField):
    type: str

class AmountField(FixedLengthMixin, DataElementField):
    type: str

class BinaryField(DataElementField):
    type: str

class IDField(FixedLengthMixin, AlphanumericField):
    type: str

class BooleanField(FixedLengthMixin, AlphanumericField):
    type: str

class CodeFieldMixin:
    def __init__(self, enum: Incomplete | None = None, *args, **kwargs) -> None: ...

class CodeField(CodeFieldMixin, AlphanumericField):
    type: str

class IntCodeField(CodeFieldMixin, NumericField):
    type: str

class CountryField(FixedLengthMixin, DigitsField):
    type: str

class CurrencyField(FixedLengthMixin, AlphanumericField):
    type: str

class DateField(FixedLengthMixin, NumericField):
    type: str

class TimeField(FixedLengthMixin, DigitsField):
    type: str

class TimestampField(DataElementField):
    type: str

class PasswordField(AlphanumericField):
    type: str

class SegmentSequenceField(DataElementField):
    type: str
