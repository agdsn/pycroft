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
from datetime import datetime, timedelta

from pycroft.model.session import session
from pycroft.model.accounting import TrafficVolume
from pycroft.model.host import Host, Ip, ARecord, CNameRecord

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


@template_filter("host_traffic")
def host_traffic_filter(host):
    traffic_timespan = datetime.now() - timedelta(days=7)

    trafficvolumes = session.query(
        TrafficVolume
    ).join(
        TrafficVolume.ip
    ).join(
        Ip.host
    ).filter(
        Host.id == host.id
    ).filter(
        TrafficVolume.timestamp > traffic_timespan
    ).all()

    traffic_sum = 0
    for traffic in trafficvolumes:
        traffic_sum += ( traffic.size / 1024 / 1024 )

    return u"%s MB" % (traffic_sum, )


@template_filter("host_name")
def host_name_filter(host):
    arecord = session.query(
        ARecord
    ).filter(
        ARecord.host_id == host.id
    ).first()

    if arecord is not None:
        return arecord.name
    else:
        return "NoName"

@template_filter("host_cname")
def host_cname_filter(host):
    cname_record = session.query(
        CNameRecord
    ).filter(
        CNameRecord.host_id == host.id
    ).first()

    if cname_record is not None:
        return cname_record.name
    else:
        return "NoCName"


@template_filter("record_editable")
def record_editable_filter(record):
    if record.discriminator == "arecord" or record.discriminator == "aaaarecord":
        return False
    else:
        return True

@template_filter("record_removable")
def record_removable_filter(record):
    if record.discriminator == "arecord" or record.discriminator == "aaaarecord":
        return False
    else:
        return True

@template_filter("record_readable_name")
def record_readable_name_filter(record):
    return record.__class__.__name__


@template_filter("level_number")
def level_number_filter(level):
        if level<10:
            return u"0%s" % (level, )
        else:
            return level

def register_filters(app):
    for name in _filter_registry:
        app.jinja_env.filters[name] = _filter_registry[name]
