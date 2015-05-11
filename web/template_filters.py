# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    web
    ~~~~~~~~~~~~~~

    This package contains the web interface based on flask

    :copyright: (c) 2012 by AG DSN.
"""
from cmath import log
from datetime import datetime, timedelta
from itertools import chain
import flask.ext.babel

from pycroft._compat import imap
from pycroft.model import session
from pycroft.model.accounting import TrafficVolume
from pycroft.model.host import Host, IP

_filter_registry = {}


def template_filter(name):
    def decorator(fn):
        _filter_registry[name] = fn
        return fn
    return decorator


_category_map = {"warning": "Warnung",
                 "error": "Fehler",
                 "info": "Hinweis",
                 "message": "Hinweis",
                 "success": "Erfolgreich"}


@template_filter("pretty_category")
def pretty_category_filter(category):
    """Make pretty category names for flash messages, etc
    """
    return _category_map.get(category, "Hinweis")


@template_filter("date")
def date_filter(dt, format=None):
    """Format date or datetime objects using Flask-Babel
    :param datetime|date|None dt: a datetime object or None
    :param str format: format as understood by Flask-Babel's format_datetime
    :rtype: unicode
    """
    if dt is None:
        return u"k/A"
    return flask.ext.babel.format_date(dt, format)


@template_filter("datetime")
def datetime_filter(dt, format=None):
    """Format datetime objects using Flask-Babel
    :param datetime|None dt: a datetime object or None
    :param str format: format as understood by Flask-Babel's format_datetime
    :rtype: unicode
    """
    if dt is None:
        return u"k/A"
    return flask.ext.babel.format_datetime(dt, format)


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

    now = session.utcnow()
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
            return "vor {:d} {}".format(period, singular if period == 1 else plural)

    return default


def prefix_unit_filter(value, unit, factor, prefixes):
    units = list(chain(unit, imap(lambda p: p + unit, prefixes)))
    if value > 0:
        n = min(int(log(value, factor).real), len(units)-1)
        #todo change decimal formatting appropriately, previous {0:,4f} is wrong
        return "{0:,f} {1}".format(float(value)/factor**n, units[n])
    else:
        return "0 {0}".format(units[0])


@template_filter("byte_size")
def byte_size_filter(value):
    return prefix_unit_filter(value, 'B', 1024, ['Ki', 'Mi', 'Gi', 'Ti'])


@template_filter("money")
def money_filter(amount):
    """Format a money string from Cents to Euro
    """
    euro = amount/100.0
    return (u"{:.2f} €".format(euro)).replace('.', ',')


@template_filter("host_traffic")
def host_traffic_filter(host):
    traffic_timespan = datetime.utcnow() - timedelta(days=7)

    traffic_volumes = session.session.query(
        TrafficVolume
    ).join(
        TrafficVolume.ip
    ).join(
        IP.host
    ).filter(
        Host.id == host.id
    ).filter(
        TrafficVolume.timestamp > traffic_timespan
    ).all()

    traffic_sum = 0
    for traffic in traffic_volumes:
        traffic_sum += ( traffic.size / 1024 / 1024 )

    return u"{} MB".format(traffic_sum)


@template_filter("host_name")
def host_name_filter(host):
    return "Not Implemented"


@template_filter("host_cname")
def host_cname_filter(host):
    return "Not Implemented"


@template_filter("record_editable")
def record_editable_filter(record):
    if record.discriminator == "a_record" or record.discriminator == "aaaa_record":
        return False
    else:
        return True


@template_filter("record_removable")
def record_removable_filter(record):
    if record.discriminator == "a_record" or record.discriminator == "aaaa_record":
        return False
    else:
        return True


@template_filter("record_readable_name")
def record_readable_name_filter(record):
    return record.__class__.__name__


#TODO: usecases — should that srsly return >1 switch?
# Because if yes, there should be a more elegant solution for providing a link
# in the table this is actually used (`user_show_devices_json()`)!
@template_filter("get_switch")
def ip_get_switch(host,ip):
    patch_ports = host.room.patch_ports
    if not patch_ports:
        return "No Switch"
    return u', '.join(imap(lambda p: p.destination_port.switch.name, patch_ports))


#TODO: usecases — should that srsly return >1 port? (see todo above)
@template_filter("get_switch_port")
def ip_get_switch_port(host,ip):
    patch_ports = host.room.patch_ports
    if not patch_ports:
        return "No Port"
    return u', '.join(imap(lambda p: p.destination_port.name, patch_ports))


def register_filters(app):
    for name in _filter_registry:
        app.jinja_env.filters[name] = _filter_registry[name]
