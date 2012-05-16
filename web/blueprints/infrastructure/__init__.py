# -*- coding: utf-8 -*-
"""
    web.blueprints.infrastructure
    ~~~~~~~~~~~~~~

    This module defines view functions for /infrastructure

    :copyright: (c) 2012 by AG DSN.
"""

from flask import Blueprint, render_template
from pycroft.model.hosts import Switch
from web.blueprints import BlueprintNavigation

bp = Blueprint('infrastructure', __name__, )
nav = BlueprintNavigation(bp, "Infrastruktur")


@bp.route('/subnets')
@nav.navigate(u"Subnetze")
def subnets():
    return render_template('infrastructure/base.html')


@bp.route('/switches')
@nav.navigate(u"Switche")
def switches():
    switches_list = Switch.q.all()
    return render_template('infrastructure/switches_list.html',
            switches=switches_list)


@bp.route('/show/<switch_id>')
def switch_show(switch_id):
    switch = Switch.q.get(switch_id)
    switch_port_list = switch.ports
    return render_template('infrastructure/switch_show.html',
        page_title=u"Switch " + switch.name, switch_ports=switch_port_list)


@bp.route('/vlans')
@nav.navigate(u"Vlans")
def vlans():
    return render_template('infrastructure/base.html')
