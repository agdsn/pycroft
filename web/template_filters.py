# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    web
    ~~~~~~~~~~~~~~

    This package contains the web interface based on flask

    :copyright: (c) 2012 by AG DSN.
"""

from functools import wraps


_filter_registry = {}


def template_filter(name):
    def decorator(fn):
        _filter_registry[name] = fn
        return fn

    return decorator


_category_map = {"warning": "Warnung",
                 "error": "Fehler",
                 "info": "Hinweis",
                 "mesage": "Hinweis",
                 "success": "Erfolgreich"}


@template_filter("pretty_category")
def pretty_category_filter(category):
    return _category_map.get(category, "Hinweis")


def register_filters(app):
    for name in _filter_registry:
        app.jinja_env.filters[name] = _filter_registry[name]
