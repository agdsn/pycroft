from flask import Blueprint

from . import v0

bp = Blueprint('api', __name__)
v0.api.init_app(bp)

def errorpage(e):
    return v0.api.handle_error(e)
