import json
from . import models as models

class JSONEncoder(json.JSONEncoder):
    def default(self, value): ...
