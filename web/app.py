import os

import jinja2.ext
from flask import (
    Flask, current_app, redirect, render_template, request, url_for,
)
from flask_babel import Babel
from flask_login import current_user
from werkzeug.datastructures import ImmutableDict

from hades_logs import HadesLogs
from pycroft.helpers.i18n import gettext
from pycroft.model import session
from web import api
from web.blueprints import task
from . import template_filters, template_tests
from .blueprints import (
    facilities, finance, infrastructure, login, properties, user, host
)

from .blueprints.login import login_manager
from .templates import page_resources
from pycroft.helpers.git_helpers import get_repo_active_branch, get_latest_commits


class PycroftFlask(Flask):
    """
    Extend the Flask class to set Jinja options.
    """
    jinja_options = ImmutableDict(
        Flask.jinja_options,
        extensions=[
            jinja2.ext.autoescape,
            jinja2.ext.do,
            jinja2.ext.loopcontrols,
            jinja2.ext.with_,
        ],
        undefined=jinja2.StrictUndefined,
    )

    def __init__(self, *a, **kw):
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

    def maybe_add_config_from_env(self, keys):
        """Write keys from the environment to the app's config

        If a key does not exist in the environment, it will just be
        skipped.

        :param keys: An iterable of strings
        """
        for key in keys:
            try:
                self.config[key] = os.environ[key]
            except KeyError:
                self.logger.debug("Config key %s not present in environment, skipping", key)
                continue
            else:
                self.logger.debug("Config key %s successfuly read from environment", key)


def make_app(debug=False):
    """  Create and configure the main? Flask app object

    :return: The fully configured app object
    """
    app = PycroftFlask(__name__)
    app.debug = debug

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

    template_filters.register_filters(app)
    template_tests.register_checks(app)

    babel = Babel(app)
    try:
        HadesLogs(app)
    except KeyError as e:
        app.logger.info("HadesLogs configuration incomplete, skipping.")
        app.logger.info("Original error: %s", str(e))

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
    def errorpage(e):
        """Handle errors according to their error code

        :param e: The error from the errorhandler
        """
        # We need this path hard-coding because the global app errorhandlers have higher
        # precedence than anything registered to a blueprint.
        # A clean solution would be flask supporting nested blueprints (see flask #539)
        if request.path.startswith('/api/'):
            return api.errorpage(e)

        if not hasattr(e, 'code'):
            code = 500
        else:
            code = e.code
        if code == 500:
            message = str(e)
        elif code == 403:
            message = gettext(u"You are not allowed to access this page.")
        elif code == 404:
            message = gettext(u"Page not found.")
        else:
            raise AssertionError()
        return render_template('error.html', error=message), code

    @app.route('/')
    def redirect_to_index():
        return redirect(url_for('user.overview'))

    @app.route('/version/')
    def version():
        pycroft_dir = './'
        return render_template('version.html',
                               active_branch=get_repo_active_branch(pycroft_dir),
                               commits=get_latest_commits(pycroft_dir, 20))

    @app.teardown_request
    def shutdown_session(exception=None):
        session.Session.remove()

    @app.before_request
    def require_login():
        """Request a login for every page
        except the login blueprint and the static folder.

        Blueprint "None" is needed for "/static/*" GET requests.
        """
        if current_user.is_anonymous and request.blueprint not in ("login", 'api', None):
            return current_app.login_manager.unauthorized()

    return app
