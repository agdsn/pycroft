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
from datetime import datetime


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
    """Make pretty category names for flash messages, etc
    """
    return _category_map.get(category, "Hinweis")


@template_filter("date")
def date_filter(dt, format="%d.%m.%Y"):
    """Pretty format a date.
    """
    if dt is None:
        return "k/A"
    return  dt.strftime(format)


@template_filter("datetime")
def datetime_filter(dt, format="%d.%m.%Y %H:%M Uhr"):
    """Pretty format a Date/Time.
    """
    if dt is None:
        return "k/A"
    return dt.strftime(format)


@template_filter("timesince")
def timesince_filter(dt, default="just now"):
    """
    Returns string representing "time since" e.g.
    3 days ago, 5 hours ago etc.

    adopted from
    http://flask.pocoo.org/snippets/33/
    """
    if dt is None:
        return "k/A"

    now = datetime.now()
    diff = now - dt

    periods = (
        (diff.days / 365, "Jahr", "Jahre"),
        (diff.days / 30, "Monat", "Monate"),
        (diff.days / 7, "Woche", "Wochen"),
        (diff.days, "Tag", "Tage"),
        (diff.seconds / 3600, "Stunde", "Stunden"),
        (diff.seconds / 60, "Minute", "Minuten"),
        (diff.seconds, "Sekunde", "Sekunden"),
    )

    for period, singular, plural in periods:

        if period:
            return "vor %d %s" % (period, singular if period == 1 else plural)

    return default


def register_filters(app):
    for name in _filter_registry:
        app.jinja_env.filters[name] = _filter_registry[name]
