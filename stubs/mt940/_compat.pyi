import configparser as configparser
import pickle as pickle
from _typeshed import Incomplete
from io import BytesIO as BytesIO, StringIO as StringIO
from string import ascii_lowercase as ascii_lowercase
from urllib.request import urlretrieve as urlretrieve

PY2: Incomplete
unichr = chr
text_type = str
string_types: Incomplete
integer_types: Incomplete

def text_to_native(s, enc): ...
def iterkeys(d): ...
def itervalues(d): ...
def iteritems(d): ...
izip = zip
imap = map
range_type = range

def cmp(a, b): ...
input = input

def console_to_str(s): ...
def reraise(tp, value, tb: Incomplete | None = ...) -> None: ...

number_types: Incomplete

# Names in __all__ with no definition:
#   _identity
