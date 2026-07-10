from ..fields import DataElementGroupField as DataElementGroupField
from ..formals import (
    Account3 as Account3,
    GetSEPAAccountParameter1 as GetSEPAAccountParameter1,
    GetSEPAAccountParameter3 as GetSEPAAccountParameter3,
    KTZ1 as KTZ1,
)
from .base import FinTS3Segment as FinTS3Segment, ParameterSegment as ParameterSegment
from _typeshed import Incomplete

class HKSPA1(FinTS3Segment):
    accounts: Incomplete

class HISPA1(FinTS3Segment):
    accounts: Incomplete

class HISPAS1(ParameterSegment):
    parameter: Incomplete

class HISPAS3(ParameterSegment):
    parameter: Incomplete
