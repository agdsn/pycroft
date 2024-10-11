import json
import typing as t
from . import models as models

class JSONEncoder(json.JSONEncoder):
    @t.override
    def default(self, value): ...
