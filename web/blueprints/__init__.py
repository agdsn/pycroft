# -*- coding: utf-8 -*-
"""
    web.blueprints
    ~~~~~~~~~~~~~~

    This package contains the blueprints of the web interface

    :copyright: (c) 2012 by AG DSN.
"""

from flask import request

class BlueprintNavigation(object):
    def __init__(self, blueprint, text, description=None):
        self.blueprint = blueprint
        self.text = text
        self.description = description
        self._elements = []

    def navigate(self, text, description=None):
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
        return len(self._elements) > 1

    @property
    def is_active(self):
        return self.blueprint.name == request.blueprint

    @property
    def first(self):
        return self._elements[0]

    @property
    def css_classes(self):
        classes = []
        if self.dropdown:
            classes.append("dropdown")
        if self.is_active:
            classes.append("active")
        return classes

    def register_on(self, app):
        if self.blueprint.name not in app.blueprints:
            raise Exception("Blueprint %s is not registred in Flask app" % self.blueprint.name)
        else:
            assert app.blueprints[self.blueprint.name] is self.blueprint, "Blueprint resistred as %s in Flask app is not the one you register navigation for!"
            if "blueprint_navigation" not in app.config:
                app.config["blueprint_navigation"] = list()
            app.config["blueprint_navigation"].append(self)