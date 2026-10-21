import typing as t

from flask import Blueprint, Flask
from flask.typing import ResponseReturnValue
from werkzeug.exceptions import HTTPException

from . import v0

bp = Blueprint("api", __name__)
v0.api.init_app(bp)


@bp.errorhandler(422)
@bp.errorhandler(400)
def handle_error(err: Exception) -> ResponseReturnValue:
    """Use `err.data` values from marshmallow for the response."""
    if not hasattr(err, "data") or not isinstance(err, HTTPException):
        return v0.api.handle_error(err)

    assert hasattr(err, "data")
    # only registered for 400/422, so the code is always set
    assert err.code is not None
    data = t.cast(dict[str, t.Any], err.data)
    headers = data.get("headers", None)
    messages = data.get("messages", ["Invalid request."])

    if headers:
        return {"errors": messages}, err.code, headers
    return {"errors": messages}, err.code


app_for_sphinx = Flask(__name__)
app_for_sphinx.register_blueprint(bp, url_prefix="/api/v0")
