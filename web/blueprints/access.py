from functools import wraps
from flask.globals import current_app
from flask import abort
from flask.ext.login import current_user, login_required
from web.blueprints import bake_endpoint


class BlueprintAccess(object):
    """This is used to restrict the access of the user according its group properties

    Every `flask.Blueprint` module should get such a `BlueprintAccess`
    instance. It is used to restrict the access to the certain view
    functions of the blueprint. For this it provides two decorators.

    The first decorator `BlueprintAccess.login_required` checks only
    if the session has a authenticated user and redirect to the login
    page if not.

    The second `BlueprintAccess.require` takes a arglist of permissions
    from which the user must have _one_. It also chechs if the user is
    authenticated. If there is no authenticated user it redirects to the
    login page. If the user have no permission it raises a 401 error.

    The usage is simple. First you instantiate a `flask.Blueprint`, and
    a `BlueprintAccess`.Then write a view function and register it on both:
        my_bp = Blueprint("test", __name__)
        my_access = BlueprintAccess(my_bp, general=[...])

        [...]

        @my_bp.route("/permission")
        @my_access.require("a_permission", "another_permission")
        def my_view_permission():
            return "Hello World"

        [...]

        @my_bp.route("/permission")
        @my_access.login_required
        def my_view_only_login():
            return "Hello World"

    The general param of the constructor holds a list of permissions
    required to access the view "in general". Its only used in a
    `BlueprintNavigation` to check if we render the first level of the
    menu entry or not.


    """
    def __init__(self, blueprint, general=None):
        """Initialize the `BlueprintAccess`.

        :param general: A list of permissions for general access.
        """
        self.blueprint = blueprint
        self._restrictions = {}

        if general is None:
            general = []
        self._general = general

    def require(self, *needed_permissions):
        """Make view function only for autorized users accessible.

        This is a decorator generator for flask view functions, It
        checks if the current session has a authenticated user and
        if the user is in a group that has _one_ of the needed
        permissions.

        The permissions are strings that are given as positional
        arguments to the decorator generator.

        """
        def decorator(fn):
            if len(needed_permissions):
                endpoint = bake_endpoint(self.blueprint, fn)
                self._restrictions[endpoint] = tuple(needed_permissions)
            @wraps(fn)
            def nufun(*args, **kwargs):
                if not current_user.is_authenticated():
                    return current_app.login_manager.unauthorized()
                if self._current_has_access(needed_permissions):
                    return fn(*args, **kwargs)
                abort(401)
            return nufun
        return decorator

    @property
    def login_required(self):
        return login_required

    def _current_has_access(self, permissions):
        user = current_user
        for perm in permissions:
            if user.has_property(perm):
                return True
        return False

    @property
    def has_general_access(self):
        """Checks if the current user has general access.

        """
        if not len(self._general):
            return True
        return self._current_has_access(self._general)

    def has_access(self, endpoint):
        """Checks if the current user has access to the given endppoint.

        :param endpoint: A endpoint name
        """
        if endpoint not in self._restrictions:
            return True
        return self._current_has_access(self._restrictions[endpoint])


def has_property(property):
    return current_user.has_property(property)
