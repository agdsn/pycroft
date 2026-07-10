from _typeshed import Incomplete
from fints.fields import (
    DataElementField as DataElementField,
    DataElementGroupField as DataElementGroupField,
    IntCodeField as IntCodeField,
)
from fints.formals import SecurityClass as SecurityClass, SegmentHeader as SegmentHeader
from fints.types import Container as Container, ContainerMeta as ContainerMeta
from fints.utils import SubclassesMixin as SubclassesMixin, classproperty as classproperty

TYPE_VERSION_RE: Incomplete

class FinTS3SegmentMeta(ContainerMeta):
    def __new__(cls, name, bases, classdict): ...

class FinTS3Segment(Container, SubclassesMixin, metaclass=FinTS3SegmentMeta):
    header: Incomplete
    def TYPE(cls): ...
    def VERSION(cls): ...
    def __init__(self, *args, **kwargs) -> None: ...
    @classmethod
    def find_subclass(cls, segment): ...

class ParameterSegment_22(FinTS3Segment):
    max_number_tasks: Incomplete
    min_number_signatures: Incomplete

class ParameterSegment(FinTS3Segment):
    max_number_tasks: Incomplete
    min_number_signatures: Incomplete
    security_class: Incomplete
