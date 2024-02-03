import os
import typing as t

import jinja2.ext
import logging
import sentry_sdk
from flask import (
    Flask,
    current_app,
    redirect,
    render_template,
    request,
    url_for,
    g,
    make_response,
    Response,
)
from flask.typing import ResponseValue, ResponseReturnValue
from flask_babel import Babel
from flask_login import current_user, LoginManager
from jinja2 import select_autoescape
from werkzeug.datastructures import ImmutableDict
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from werkzeug.exceptions import HTTPException

from hades_logs import HadesLogs
from pycroft.helpers.i18n import gettext
from pycroft.model import session
from web import api
from web.blueprints import task
from . import template_filters, template_tests
from .blueprints import (
    facilities, finance, infrastructure, login, properties, user, host, health
)

from .blueprints.login import login_manager
from .commands import register_commands
from .templates import page_resources


class PycroftFlask(Flask):
    """
    Extend the Flask class to set Jinja options.
    """
    jinja_options = ImmutableDict(
        Flask.jinja_options,
        extensions=[
            jinja2.ext.do,
            jinja2.ext.loopcontrols,
        ],
        autoescape=select_autoescape(),
        undefined=jinja2.StrictUndefined,
    )

    login_manager: LoginManager

    def __init__(self, *a: t.Any, **kw: t.Any) -> None:
        super().__init__(*a, **kw)
        # config keys to support:
        self.maybe_add_config_from_env([
            'PYCROFT_API_KEY',
            'HADES_CELERY_APP_NAME',
            'HADES_BROKER_URI',
            'HADES_RESULT_BACKEND_URI',
            'HADES_TIMEOUT',
            'HADES_ROUTING_KEY',
        ])

    def maybe_add_config_from_env(self, keys: t.Iterable[str]) -> None:
        """Write keys from the environment to the app's config

        If a key does not exist in the environment, it will just be
        skipped.
        """
        for key in keys:
            try:
                self.config[key] = os.environ[key]
            except KeyError:
                self.logger.debug("Config key %s not present in environment, skipping", key)
                continue
            else:
                self.logger.debug("Config key %s successfuly read from environment", key)


def make_app(hades_logs: bool = True) -> PycroftFlask:
    """Create and configure the main? Flask app object"""
    app = PycroftFlask(__name__)

    # initialization code
    login_manager.init_app(app)
    app.register_blueprint(user.bp, url_prefix="/user")
    app.register_blueprint(facilities.bp, url_prefix="/facilities")
    app.register_blueprint(infrastructure.bp, url_prefix="/infrastructure")
    app.register_blueprint(properties.bp, url_prefix="/properties")
    app.register_blueprint(finance.bp, url_prefix="/finance")
    app.register_blueprint(host.bp, url_prefix="/host")
    app.register_blueprint(task.bp, url_prefix="/task")
    app.register_blueprint(login.bp)
    app.register_blueprint(api.bp, url_prefix="/api/v0")
    app.register_blueprint(health.bp, url_prefix="/health")

    template_filters.register_filters(app)
    template_tests.register_checks(app)

    # NOTE: this is _only_ used for its datetime formatting capabilities,
    # for translations we have our own babel interface in `pycroft.helpers.i18n.babel`!
    Babel(app)
    if hades_logs:
        try:
            HadesLogs(app)
        except KeyError as e:
            app.logger.info("HadesLogs configuration incomplete, skipping.")
            app.logger.info("Original error: %s", str(e))
    else:
        app.logger.info("HadesLogs configuration disabled. Skipping.")

    page_resources.init_app(app)

    user.nav.register_on(app)
    finance.nav.register_on(app)
    facilities.nav.register_on(app)
    infrastructure.nav.register_on(app)
    task.nav.register_on(app)
    properties.nav.register_on(app)

    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(500)
    def errorpage(e: Exception) -> ResponseReturnValue:
        """Handle errors according to their error code

        :param e: The error from the errorhandler
        """
        # We need this path hard-coding because the global app errorhandlers have higher
        # precedence than anything registered to a blueprint.
        # A clean solution would be flask supporting nested blueprints (see flask #539)
        if request.path.startswith('/api/'):
            return api.errorpage(e)

        code = getattr(e, "code", 500)

        if code == 500:
            message = str(e)
        elif code == 403:
            message = gettext("You are not allowed to access this page.")
        elif code == 404:
            message = gettext("Page not found.")
        else:
            raise AssertionError()
        return render_template('error.html', error=message), code

    @app.route('/')
    def redirect_to_index() -> ResponseValue:
        return redirect(url_for('user.overview'))

    @app.route('/debug-sentry')
    def debug_sentry() -> t.NoReturn:
        app.logger.warning("Someone used the debug-sentry endpoint! Also, this is a test warning.")
        app.logger.info("An info log for inbetween")
        app.logger.error("Someone used the debug-sentry endpoint! Also, this is a test error.",
                         extra={'pi': 3.141})
        div_by_zero = 1 / 0  # noqa
        assert False  # noqa: B011

    @app.teardown_request
    def shutdown_session(exception: BaseException | None = None) -> None:
        if app.testing:
            # things are not necessarily committed here,
            # so `remove` would result in a `ROLLBACK TO SAVEPOINT` to a pre-setup state.
            return

        session.Session.remove()

    @app.before_request
    def require_login() -> ResponseReturnValue | None:
        """Request a login for every page
        except the login blueprint and the static folder.

        Blueprint "None" is needed for "/static/*" GET requests.
        """
        if current_user.is_anonymous and request.blueprint not in (
            "login",
            "api",
            "health",
            None,
        ):
            lm = t.cast(LoginManager, current_app.login_manager)  # type: ignore[attr-defined]
            return lm.unauthorized()
        return None

    if app.debug:
        register_pyinstrument(app)
    register_commands(app)

    return app


def register_pyinstrument(app: Flask) -> None:
    try:
        from pyinstrument import Profiler
    except ImportError:
        app.logger.info("in debug mode, but pyinstrument not installed.")
        return

    @app.before_request
    def before_request() -> None:
        if "profile" in request.args:
            g.profiler = Profiler()
            g.profiler.start()

    @app.after_request
    def after_request(response: Response) -> Response:
        if not hasattr(g, "profiler"):
            return response
        g.profiler.stop()
        output_html = g.profiler.output_html()
        return make_response(output_html)

IGNORED_EXCEPTION_TYPES = (HTTPException,)


if dsn := os.getenv('PYCROFT_SENTRY_DSN'):
    _TE = t.TypeVar("_TE")

    def before_send(event: _TE, hint: dict[str, t.Any]) -> _TE | None:
        if 'exc_info' in hint:
            exc_type, exc_value, _tb = hint['exc_info']
            if isinstance(exc_value, IGNORED_EXCEPTION_TYPES):
                return None
        return event

    logging_integration = LoggingIntegration(
        level=logging.INFO,  # INFO / WARN create breadcrumbs, just as SQL queries
        event_level=logging.ERROR,  # errors and above create breadcrumbs
    )

    sentry_sdk.init(
        dsn=dsn,
        integrations=[FlaskIntegration(), logging_integration],
        traces_sample_rate=1.0,
        before_send=before_send
    )
