from flask import Blueprint
from flask.typing import ResponseReturnValue

from hades_logs import hades_logs
from hades_logs.exc import HadesError

bp = Blueprint("health", __name__)


@bp.route("hades-logs")
def hades() -> ResponseReturnValue:
    try:
        hades_logs.fetch_logs(nasipaddress="10.160.0.75", nasportid="2/1/39")
    except HadesError as e:
        return f"CRIT {e}"
    else:
        return "OK"
