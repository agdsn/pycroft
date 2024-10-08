# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from __future__ import annotations
import typing as t
from dataclasses import dataclass, field

from flask import request, url_for, Blueprint, Flask
from web.blueprints.access import BlueprintAccess
from web.blueprints import bake_endpoint


class BlueprintNavigation:
    """This is the blueprint navigation mechanism.

    Every `flask.Blueprint` module should get such a `BlueprintNavigation`
    instance. It is used to render the first- and second-level navigation
    within the top navigation bar.

    The usage is very simple: first you instantiate a `flask.Blueprint`, and
    a `BlueprintNavigation`.Then write a view function and register it on both:

        my_bp = Blueprint("test", __name__)
        my_nav = BlueprintNavigation(my_bp, "Test")

        [...]

        @my_bp.route("/")
        @my_nav.navigate("Test entry")
        def my_view():
            return "Hello World"

    Then, if you have a `flask.Flask` instance anywhere and register the
    blueprint, do also register the `BlueprintNavigation`:

        app = flask.Flask(...)

        app.register_blueprint(my_bp)
        my_nav.register_on(app)

    Do not forget to import my_nav and my_bp. The rendering is handled in
    the templates.

    It can use a `BlueprintAccess` instance to announce only navigations
    that are accessible for the current user.
    """

    def __init__(
        self,
        blueprint: Blueprint,
        text: str,
        icon: str | None = None,
        description: str | None = None,
        blueprint_access: BlueprintAccess | None = None,
        push_right: bool = False,
    ):
        """Init the `BlueprintNavigation` instance.

        :param blueprint: A `flask.Blueprint` instance.
        :param text: The text for the top bar navigation.
        :param description: An optional anchor title.
        """
        self.blueprint: Blueprint = blueprint
        self.text = text
        self.icon = icon
        self.description = description
        self._elements: list[NavigationItem] = []
        if blueprint_access is None:
            blueprint_access = BlueprintAccess(blueprint)
        self._access = blueprint_access
        self.push_right = push_right

    @property
    def is_allowed(self) -> bool:
        """Checks if the user has general access to the blueprint.

        This uses the `BlueprintAccess.is_accessible` to find out
        if the user has access to this blueprint (and its navigation).

        If there is no `BlueprintAccess` given we assume everything
        is granted.
        """
        return self._access.is_accessible

    def navigate[
        TFun: t.Callable
    ](
        self,
        text: str,
        weight: int = 0,
        description: str | None = None,
        icon: str | None = None,
    ) -> t.Callable[[TFun], TFun]:
        """A decorator to add a navigation menu entry for the actual view func.

        This is a decorator like the "route()" from `flask.Flask` or
        `flask.Blueprint`. It register a navigation menu entry for the
        current view function.
        The text argument is used as menu-text and the description sets an
        optional anchor-title.

        :param text: The menu entry text.
        :param description: a anchor title.
        :param weight: weight (i.e. priority) of the object.
        """

        def decorator(f: TFun) -> TFun:
            self._elements.append(NavigationItem(
                endpoint=bake_endpoint(self.blueprint, f),
                text=text,
                description=description,
                icon=icon,
                weight=weight
            ))
            self._elements.sort(key=lambda entry: entry.weight)
            # TODO: Sort this list
            return f
        return decorator

    def __iter__(self) -> t.Iterator[NavigationItem]:
        """Get all navigation elements the user has access to.

        If there is a `BlueprintAccess` instance given to this navigation
        then its used to no show navigation elements which the user has no
        access to. For this the `BlueprintNavigation.is_endpoint_accessible()` is used.

        If no `BlueprintAccess` was set we assume that everything is
        granted.
        """
        for element in self._elements:
            if self._access.is_endpoint_accessible(element.endpoint):
                yield element

    @property
    def dropdown(self) -> bool:
        """Checks if the menu element needs a dropdown

        `BlueprintNavigation` instances with only one navigable view
        function does not get a dropdown. They are rendered as single links
        within the top navigation bar. This property tells if there will be
        a dropdown or not.

        :return: True its rendered as dropdown.
        """
        return len(self._elements) > 1

    @property
    def is_active(self) -> bool:
        """Tells if the blueprint of this instance is active.

        Active is a blueprint if a view func of it is shown.

        :return: True if active, False else.
        """
        # TODO remove these casts once on `Flask v2`
        return t.cast(str, self.blueprint.name) == t.cast(str, request.blueprint)

    @property
    def get_page_title(self) -> str | None:
        """Returns the active element of the instance, or nil"""

        for element in self._elements:
            if url_for(element.endpoint) == request.path:
                return element.text
        return None

    @property
    def first(self) -> NavigationItem:
        """Get the first registered view function.

        This is used for non-dropdown rendering.

        :return: The first navigation element.
        """
        return self._elements[0]

    @property
    def css_classes(self) -> list[str]:
        """Get the css classes for a top-level <li> menu element.

        :return: A list of strings.
        """
        classes = ['nav-item']
        if self.dropdown:
            classes.append("dropdown")
        if self.is_active:
            classes.append("active")
        return classes

    def register_on(self, app: Flask) -> None:
        """This registers the `BlueprintNavigation` for the Flask app.

        This uses a `list` in the flask config object to register the
        navigation. The key for the `list` is "blueprint_navigation".

        The template iterates over this list and renders the navigation
        elements. The order the elements are registered is the order the
        elements will be shown.

        :param app: A flask app
        """

        if self.blueprint.name not in app.blueprints:
            raise Exception("Blueprint {} is not registred in Flask app".format(
                            self.blueprint.name))
        else:
            assert app.blueprints[self.blueprint.name] is self.blueprint, \
            "Blueprint resistred as {} in Flask app is not the one you " \
            "register navigation for!"

            app.config.setdefault('blueprint_navigation', SegmentedList())\
                .append(self, right=self.push_right)
        return


@dataclass
class SegmentedList[TElem]:
    left: list[TElem] = field(default_factory=lambda: [])
    right: list[TElem] = field(default_factory=lambda: [])

    def append(self, element: TElem, right: bool = False) -> None:
        (self.right if right else self.left).append(element)
        return

    def __iter__(self) -> t.Iterator[TElem]:
        yield from self.left
        yield from self.right


@dataclass
class NavigationItem:
    endpoint: str
    text: str
    description: str
    icon: str
    weight: int
