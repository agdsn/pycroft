# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    web.blueprints
    ~~~~~~~~~~~~~~

    This package contains the blueprints of the web interface

    :copyright: (c) 2012 by AG DSN.
"""

from flask import request

class BlueprintNavigation(object):
    """This is the blueprint navigation mechanism.

    Every `flask.Blueprint` module should get such a `BlueprintNavigation`
    instance. It is used to render the first- and second-level navigation
    within the top navigation bar.

    The usage is very simple: first you instantiate a `flask.Blueprint`, and
    a `BlueprintNavigation`. Then write a view function and register it on both:

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
    """
    # ToDo: filter navigation rendering according the privileges of the user

    def __init__(self, blueprint, text, description=None):
        """Init the `BlueprintNavigation` instance.

        :param blueprint: A `flask.Blueprint` instance.
        :param text: The text for the top bar navigation.
        :param description: An optional anchor title.
        """
        self.blueprint = blueprint
        self.text = text
        self.description = description
        self._elements = []

    def navigate(self, text, description=None):
        """A decorator to add a navigation menu entry for the actual view func.

        This is a decorator like the "route()" from `flask.Flask` or
        `flask.Blueprint`. It register a navigation menu entry for the
        current view function.
        The text argument is used as menu-text and the description sets an
        optional anchor-title.

        :param text: The menu entry text.
        :param description: a anchor title.
        """
        def decorator(f):
            element = self._navigation_item("%s.%s" % (self.blueprint.name, f.__name__),
                                                text,
                                                description)
            self._elements.append(element)
            return f
        return decorator

    def _navigation_item(self, endpoint, text, description=None):
        return {"endpoint": endpoint,
                "text": text,
                "description": description}

    def __iter__(self):
        return self._elements.__iter__()

    @property
    def dropdown(self):
        """Checks if the menu element needs a dropdown

        `BlueprintNavigation` instances with only one navigateable view
        function does not get a dropdown. They are rendered as single links
        within the top navigation bar. This property tells if there will be
        a dropdown or not.

        :return: True its rendered as dropdown.
        """
        return len(self._elements) > 1

    @property
    def is_active(self):
        """Tells if the blueprint of this instance is active.

        Active is a blueprint if a view func of it is shown.

        :return: True if active, False else.
        """
        return self.blueprint.name == request.blueprint

    @property
    def first(self):
        """Get the first registered view function.

        This is used for non-dropdown rendering.

        :return: The first navigation element.
        """
        return self._elements[0]

    @property
    def css_classes(self):
        """Get the css classes for a top-level <li> menu element.

        :return: A list of strings.
        """
        classes = []
        if self.dropdown:
            classes.append("dropdown")
        if self.is_active:
            classes.append("active")
        return classes

    def register_on(self, app):
        """This registers the `BlueprintNavigation` for the Flask app.

        This uses a `list` in the flask config object to register the
        navigation. The key for the `list` is "blueprint_navigation".

        The template iterates over this list and renders the navigation
        elements. The order the elements are registered is the order the
        elements will be shown.

        :param app: A `flask.Flask` application instance.
        """

        if self.blueprint.name not in app.blueprints:
            raise Exception("Blueprint %s is not registred in Flask app" % self.blueprint.name)
        else:
            assert app.blueprints[self.blueprint.name] is self.blueprint, "Blueprint resistred as %s in Flask app is not the one you register navigation for!"
            if "blueprint_navigation" not in app.config:
                app.config["blueprint_navigation"] = list()
            app.config["blueprint_navigation"].append(self)
