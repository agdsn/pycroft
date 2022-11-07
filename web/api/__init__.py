from flask import Blueprint, Flask

from . import v0

bp = Blueprint('api', __name__)
v0.api.init_app(bp)

app_for_sphinx = Flask(__name__)
app_for_sphinx.register_blueprint(bp, url_prefix="/api/v0")

def errorpage(e):
    return v0.api.handle_error(e)
