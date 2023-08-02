# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import typing as t
from itertools import chain
from flask.globals import current_app
from flask import request, Blueprint, abort
from flask_login import current_user
from werkzeug.wrappers import BaseResponse

from web.blueprints import bake_endpoint


TFun = t.TypeVar("TFun", bound=t.Callable)


def _check_properties(properties: t.Iterable[str]) -> bool:
    missing_props = set(properties) - current_user.current_properties_set
    return not missing_props


class BlueprintAccess:
    """A Blueprint that requires accessing users to have a set of properties.

    Every `flask.Blueprint` module should be augmented with a `BlueprintAccess`
    instance. It is used to restrict the access to the view functions of the
    blueprint.

    Access restrictions can be defined globally for the whole blueprint or on a
    per-view function basis. Per-view restrictions do not override global
    restrictions, they are additional.

    Global restrictions are set with the `BlueprintAccess` objects
    `required_properties` argument, per-view restrictions are set by providing
     a `required_properties` argument to the `Blueprint.route` decorator method.

    If the session does not have an authenticated user, `Flask-Login`'s
    `unauthorized` logic is invoked. This should usually result in the user
    being redirected to the login page, see the `Flask-Login` documentation for
    more information.

    If the user lacks a required property, either global or per-view the request
    will be aborted with a 403 error, that can be handled through a
    `Flask.error_handler`.

    The usage is simple. First you instantiate a `flask.Blueprint`, and
    a `BlueprintAccess`.Then write a view function and register it on both:
    ```
        my_bp = Blueprint("test", __name__)
        my_access = BlueprintAccess(my_bp, required_properties=["test_show"])

        @my_bp.route("/protected")
        @my_access.require_properties("test_delete", "test_admin")
        def my_protected_view):
            return "Hello World"
    """

    def __init__(self, blueprint: Blueprint, required_properties: t.Iterable[str] = ()):
        """Initialize the `BlueprintAccess`.

        :param required_properties: An iterable of properties that
        are required to access any view function in the blueprint.
        """
        self.blueprint = blueprint
        self.required_properties = tuple(required_properties)
        self.endpoint_properties_map: dict[str, tuple[str, ...]] = {}
        blueprint.before_request(self._check_access)

    def require(self, *required_properties: str) -> t.Callable[[TFun], TFun]:
        """Set per-view function restrictions.

        Decorate flask view functions with this decorator to specify properties
        a user must have in order to access the view function.
        :param required_properties: Names of the properties that are
        required.
        """
        view_properties = required_properties

        def decorator(f: TFun) -> TFun:
            endpoint = bake_endpoint(self.blueprint, f)
            self.endpoint_properties_map[endpoint] = view_properties
            f.required_properties = view_properties  # type: ignore[attr-defined]
            return f
        return decorator

    def _check_access(self) -> BaseResponse | None:
        if not current_user.is_authenticated:
            return t.cast(BaseResponse, current_app.login_manager.unauthorized())  # type: ignore[attr-defined]
        endpoint = request.endpoint
        properties = chain(self.required_properties,
                           self.endpoint_properties_map.get(endpoint, ()))
        if not _check_properties(properties):
            abort(403)
        return None

    @property
    def is_accessible(self) -> bool:
        """Checks if the current user may access this blueprint."""
        return _check_properties(self.required_properties)

    def is_endpoint_accessible(self, endpoint: str) -> bool:
        """Checks if the current user may access the given endpoint.

        :param endpoint: A endpoint name
        """
        endpoint_specific = self.endpoint_properties_map.get(endpoint, ())
        return _check_properties(chain(self.required_properties,
                                       endpoint_specific))
