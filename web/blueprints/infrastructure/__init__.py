# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    web.blueprints.infrastructure
    ~~~~~~~~~~~~~~

    This module defines view functions for /infrastructure

    :copyright: (c) 2012 by AG DSN.
"""

from flask import (
    Blueprint, abort, flash, jsonify, redirect, render_template,url_for)
from sqlalchemy.orm import joinedload
from pycroft.helpers import net
from pycroft.model import session
from pycroft.model.host import Switch, SwitchPort
from pycroft.model.net import VLAN, Subnet
from pycroft.model.port import PatchPort
from web.blueprints.navigation import BlueprintNavigation
from web.blueprints.access import BlueprintAccess
from .tables import SubnetTable, SwitchTable, VlanTable, PortTable

bp = Blueprint('infrastructure', __name__)
access = BlueprintAccess(bp, required_properties=['infrastructure_show'])
nav = BlueprintNavigation(bp, "Infrastruktur", blueprint_access=access)


@bp.route('/subnets')
@nav.navigate(u"Subnetze")
def subnets():
    return render_template(
        'infrastructure/subnets_list.html',
        subnet_table=SubnetTable(data_url=url_for(".subnets_json")))


@bp.route('/subnets/json')
def subnets_json():
    subnets_list = Subnet.q.all()
    return jsonify(items=[{
            'id': subnet.id,
            'description': subnet.description,
            'address': str(subnet.address),
            'gateway': str(subnet.gateway),
        } for subnet in subnets_list])


@bp.route('/switches')
@nav.navigate(u"Switche")
def switches():
    return render_template(
        'infrastructure/switches_list.html',
        switch_table=SwitchTable(data_url=url_for(".switches_json")))


@bp.route('/switches/json')
def switches_json():
    return jsonify(items=[{
            'id': switch.host_id,
            'name': {
                'title': switch.name,
                'href': url_for(".switch_show", switch_id=switch.host_id)
            },
            'ip': str(switch.management_ip)
        } for switch in Switch.q.all()])


@bp.route('/switch/show/<int:switch_id>')
def switch_show(switch_id):
    switch = Switch.q.get(switch_id)
    if not switch:
        flash(u"Switch mit ID {} nicht gefunden!".format(switch_id), "error")
        return redirect(url_for('.switches'))
    return render_template(
        'infrastructure/switch_show.html',
        page_title=u"Switch: " + switch.name,
        switch=switch,
        port_table=PortTable(
            data_url=url_for('.switch_show_json', switch_id=switch.host_id)))


@bp.route('/switch/show/<int:switch_id>/json')
def switch_show_json(switch_id):
    switch = Switch.q.options(
        joinedload(Switch.ports).joinedload(SwitchPort.patch_port).joinedload(
            PatchPort.room)).get(switch_id)
    if not switch:
        abort(404)
    switch_port_list = switch.ports
    switch_port_list = net.sort_ports(switch_port_list)
    return jsonify(items=[{
            "portname": port.name,
            "room": {
                "href": url_for(
                    "facilities.room_show",
                    room_id=port.patch_port.room.id
                ),
                "title": "{}-{}".format(
                    port.patch_port.room.level,
                    port.patch_port.room.number
                )
            } if port.patch_port else None
        } for port in switch_port_list])


@bp.route('/vlans')
@nav.navigate(u"VLANs")
def vlans():
    return render_template(
        'infrastructure/vlan_list.html',
        vlan_table=VlanTable(data_url=url_for(".vlans_json")))


@bp.route('/vlans/json')
def vlans_json():
    return jsonify(items=[{
            'id': vlan.id,
            'name': vlan.name,
            'vid': vlan.vid,
        } for vlan in VLAN.q.all()])
