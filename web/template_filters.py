# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    web
    ~~~~~~~~~~~~~~

    This package contains the web interface based on flask

    :copyright: (c) 2012 by AG DSN.
"""
import pathlib
from cmath import log
from itertools import chain
from re import sub

import flask_babel
from flask import current_app, json, url_for
from jinja2 import contextfilter
from jinja2.runtime import Context

from pycroft.helpers.i18n import localized, gettext
from pycroft.model import session

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

template_filter("localized")(localized)


class AssetNotFound(Exception):
    pass


# noinspection PyUnusedLocal
@template_filter("require")
@contextfilter
def require(ctx: Context, asset: str, **kwargs) -> str:
    """
    Build an URL for an asset generated by webpack.

    To prevent Jinja2 from inlining the calls of this filter with constant
    parameters, this filter needs to be declared as a context filter. The
    context is not actually used.
    :param ctx: Template context
    :param asset: Name of the
    :param kwargs: Kwargs for :func:`url_for`
    :return: URL
    """
    asset_map, has_changed = current_app.extensions.get('webpack', (None, None))
    if asset_map is None or has_changed():
        path = pathlib.Path(current_app.static_folder, 'manifest.json')
        current_app.logger.info("Loading webpack manifest from %s", path)
        try:
            mtime = path.stat().st_mtime
        except FileNotFoundError as e:
            raise RuntimeError("manifest.json not found. Did you forget"
                               " to execute webpack? You might want to"
                               " take a look at the readme.md.") from e
        with path.open() as f:
            asset_map = json.load(f)

        def has_changed():
            try:
                return path.stat().st_mtime != mtime
            except OSError:
                return False

        current_app.extensions['webpack'] = asset_map, has_changed

    try:
        filename = asset_map[asset]
    except KeyError:
        raise AssetNotFound(f"Asset {asset} not found") from None
    kwargs['filename'] = filename
    return url_for('static', **kwargs)


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
        return "k/A"
    return flask_babel.format_date(dt, format)


@template_filter("datetime")
def datetime_filter(dt, format=None):
    """Format datetime objects using Flask-Babel
    :param datetime|None dt: a datetime object or None
    :param str format: format as understood by Flask-Babel's format_datetime
    :rtype: unicode
    """
    if dt is None:
        return "k/A"
    return flask_babel.format_datetime(dt, format)


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
            return f"vor {period:d} {singular if period == 1 else plural}"

    return default


def prefix_unit_filter(value, unit, factor, prefixes):
    units = list(chain(unit, (p + unit for p in prefixes)))
    if value > 0:
        n = min(int(log(value, factor).real), len(units)-1)
        #todo change decimal formatting appropriately, previous {0:,4f} is wrong
        return f"{float(value)/factor**n:,f} {units[n]}"

    return f"0 {units[0]}"


@template_filter("byte_size")
def byte_size_filter(value):
    return prefix_unit_filter(value, 'B', 1024, ['Ki', 'Mi', 'Gi', 'Ti'])


@template_filter("money")
def money_filter(amount):
    return (f"{amount:.2f}\u202f€").replace('.', ',')


@template_filter("icon")
def icon_filter(icon_class: str):
    if len(tokens := icon_class.split(maxsplit=1)) == 2:
        prefix, icon = tokens
    else:
        prefix = 'fas'
        [icon] = tokens
    return f"{prefix} {icon}"


@template_filter("account_type")
def account_type_filter(account_type):
    types = {
        "USER_ASSET": gettext("User account (asset)"),
        "BANK_ASSET": gettext("Bank account (asset)"),
        "ASSET": gettext("Asset account"),
        "LIABILITY": gettext("Liability account"),
        "REVENUE": gettext("Revenue account"),
        "EXPENSE": gettext("Expense account"),
        "LEGACY": gettext("Legacy account"),
    }

    return types.get(account_type)


@template_filter("transaction_type")
def transaction_type_filter(credit_debit_type):
    def replacer(types):
        return types and tuple(sub(r'[A-Z]+_(?=ASSET)', r'', t) for t in types)

    types = {
        ("ASSET", "LIABILITY"): gettext("Balance sheet extension"),
        ("LIABILITY", "ASSET"): gettext("Balance sheet contraction"),
        ("ASSET", "REVENUE"): gettext("Revenue"),
        ("REVENUE", "ASSET"): gettext("Correcting entry (Revenue)"),
        ("EXPENSE", "ASSET"): gettext("Expense"),
        ("ASSET", "EXPENSE"): gettext("Correcting entry (Expense)"),
        ("ASSET", "ASSET"): gettext("Asset exchange"),
        ("LIABILITY", "LIABILITY"): gettext("Liability exchange")
    }
    return types.get(replacer(credit_debit_type), gettext("Unknown"))


"""
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
"""


def register_filters(app):
    for name in _filter_registry:
        app.jinja_env.filters[name] = _filter_registry[name]
