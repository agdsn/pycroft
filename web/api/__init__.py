from flask import Blueprint, jsonify

from . import v0

bp = Blueprint('api', __name__)
v0.api.init_app(bp)

def errorpage(e):
    code = getattr(e, 'code', 500)
    if code == 404:
        return jsonify(msg=str(e))
    return jsonify(msg="error", code=code)
