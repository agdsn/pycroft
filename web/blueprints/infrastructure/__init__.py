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

from flask import Blueprint, flash, redirect, render_template, url_for, jsonify, \
    abort
from pycroft.helpers import net
from pycroft.model import session
from pycroft.model.host import Switch
from pycroft.model.net import VLAN, Subnet
from pycroft.model.dns import Record, CNAMERecord
from web.blueprints.navigation import BlueprintNavigation
from web.blueprints.infrastructure.forms import SwitchPortForm
from web.blueprints.infrastructure.forms import CNAMERecordEditForm
from web.blueprints.infrastructure.forms import CNAMERecordCreateForm
from web.blueprints.infrastructure.forms import RecordCreateForm
from web.blueprints.access import BlueprintAccess

bp = Blueprint('infrastructure', __name__, )
access = BlueprintAccess(bp, ['infrastructure_show'])
nav = BlueprintNavigation(bp, "Infrastruktur", blueprint_access=access)


@bp.route('/subnets')
@nav.navigate(u"Subnetze")
@access.require('infrastructure_show')
def subnets():
    return render_template('infrastructure/subnets_list.html')


@bp.route('/subnets/json')
@access.require('infrastructure_show')
def subnets_json():
    subnets_list = Subnet.q.all()
    return jsonify(items=[{
            'id': subnet.id,
            # TODO href to DNS zones
            'primary_dns_zone': subnet.primary_dns_zone,
            'reverse_dns_zone': subnet.reverse_dns_zone,
            'address': str(subnet.address),
            'gateway': subnet.gateway,
        } for subnet in subnets_list])


@bp.route('/switches')
@nav.navigate(u"Switche")
@access.require('infrastructure_show')
def switches():
    return render_template('infrastructure/switches_list.html')


@bp.route('/switches/json')
@access.require('infrastructure_show')
def switches_json():
    return jsonify(items=[{
            'id': switch.id,
            'name': {
                'title': switch.name,
                'href': url_for(".switch_show", switch_id=switch.id)
            },
            'ip': switch.management_ip
        } for switch in Switch.q.all()])


@bp.route('/user/<int:user_id>/record_delete/<int:record_id>')
@access.require('infrastructure_change')
def record_delete(user_id, record_id):
    record = Record.q.get(record_id)
    session.session.delete(record)
    session.session.commit()
    flash(u"Record gelöscht", 'success')

    return redirect(url_for("user.user_show", user_id=user_id))


@bp.route('/user/<int:user_id>/record_edit/<int:record_id>',
    methods=['GET', 'POST'])
@access.require('infrastructure_change')
def record_edit(user_id, record_id):
    record = Record.q.get(record_id)

    edit_function = ".{}_edit".format(record.discriminator,)

    return redirect(
        url_for(edit_function, user_id=user_id, record_id=record_id))


@bp.route('/user/<int:user_id>/record_edit/<int:record_id>/a')
@access.require('infrastructure_change')
def a_record_edit(user_id, record_id):
    return redirect(url_for("user.user_show", user_id=user_id))


@bp.route('/user/<int:user_id>/record_edit/<int:record_id>/aaaa')
@access.require('infrastructure_change')
def aaaa_record_edit(user_id, record_id):
    return redirect(url_for("user.user_show", user_id=user_id))


@bp.route('/user/<int:user_id>/record_edit/<int:record_id>/cname',
    methods=['GET', 'POST'])
@access.require('infrastructure_change')
def cname_record_edit(user_id, record_id):
    record = CNAMERecord.q.get(record_id)

    form = CNAMERecordEditForm()
    form.record_for.data = record.record_for.name

    if form.validate_on_submit():
        record.name = form.name.data
        session.session.commit()
        flash(u"Alias geändert", "success")
        return redirect(url_for("user.user_show", user_id=user_id))

    return render_template('infrastructure/record_edit.html',
        form=form, user_id=user_id,
        page_title=u"Alias ändern für " + record.alias_for.name)


@bp.route('/user/<int:user_id>/record_edit/<int:record_id>/mx')
@access.require('infrastructure_change')
def mx_record_edit(user_id, record_id):
    return redirect(url_for("user.user_show", user_id=user_id))


@bp.route('/user/<int:user_id>/record_edit/<int:record_id>/ns')
@access.require('infrastructure_change')
def ns_record_edit(user_id, record_id):
    return redirect(url_for("user.user_show", user_id=user_id))


@bp.route('/user/<int:user_id>/record_edit/<int:record_id>/srv')
@access.require('infrastructure_change')
def srv_record_edit(user_id, record_id):
    return redirect(url_for("user.user_show", user_id=user_id))


@bp.route('/user/<int:user_id>/record_create/<int:host_id>',
    methods=['GET', 'POST'])
@access.require('infrastructure_change')
def record_create(user_id, host_id):
    form = RecordCreateForm()

    if not form.is_submitted():
        form.type.data = 'CNAMERecord'

    if form.validate_on_submit():
        create_function = ".{}_create".format(form.type.data,)

        return redirect(url_for(create_function, user_id=user_id,
            host_id=host_id))

    return render_template('infrastructure/record_create.html',
        form=form, user_id=user_id, host_id=host_id,
        page_title=u"DNS-Eintrag erzeugen")


@bp.route('/user/<int:user_id>/record_create/<int:host_id>/a')
@access.require('infrastructure_change')
def a_record_create(user_id, host_id):
    return redirect(url_for("user.user_show", user_id=user_id))


@bp.route('/user/<int:user_id>/record_create/<int:host_id>/aaaa')
@access.require('infrastructure_change')
def aaaa_record_create(user_id, host_id):
    return redirect(url_for("user.user_show", user_id=user_id))


@bp.route('/user/<int:user_id>/record_create/<int:host_id>/cname',
    methods=['GET', 'POST'])
@access.require('infrastructure_change')
def cname_record_create(user_id, host_id):
    return redirect(url_for("user.user_show", user_id=user_id))


@bp.route('/user/<int:user_id>/record_create/<int:host_id>/mx')
@access.require('infrastructure_change')
def mx_record_create(user_id, host_id):
    return redirect(url_for("user.user_show", user_id=user_id))


@bp.route('/user/<int:user_id>/record_create/<int:host_id>/ns')
@access.require('infrastructure_change')
def ns_record_create(user_id, host_id):
    return redirect(url_for("user.user_show", user_id=user_id))


@bp.route('/user/<int:user_id>/record_create/<int:host_id>/srv')
@access.require('infrastructure_change')
def srv_record_create(user_id, host_id):
    return redirect(url_for("user.user_show", user_id=user_id))


@bp.route('/switch/show/<int:switch_id>')
@access.require('infrastructure_show')
def switch_show(switch_id):
    switch = Switch.q.get(switch_id)
    if not switch:
        flash(u"Switch mit ID {} nicht gefunden!".format(switch_id), "error")
        return redirect(url_for('.switches'))
    return render_template('infrastructure/switch_show.html',
                           page_title=u"Switch: " + switch.name,
                           switch=switch)


@bp.route('/switch/show/<int:switch_id>/json')
@access.require('infrastructure_show')
def switch_show_json(switch_id):
    switch = Switch.q.get(switch_id)
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
            }
        } for port in switch_port_list])


@bp.route('/vlans')
@nav.navigate(u"VLANs")
@access.require('infrastructure_show')
def vlans():
    return render_template('infrastructure/vlan_list.html')


@bp.route('/vlans/json')
@access.require('infrastructure_show')
def vlans_json():
    return jsonify(items=[{
            'id': vlan.id,
            'name': vlan.name,
            'tag': vlan.tag
        } for vlan in VLAN.q.all()])
