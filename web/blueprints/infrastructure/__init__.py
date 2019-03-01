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
from flask_login import current_user
from flask_wtf import FlaskForm as Form
from ipaddr import IPAddress
from sqlalchemy.orm import joinedload

from pycroft.lib.infrastructure import create_switch, \
    edit_switch, delete_switch, create_switch_port, patch_switch_port_to_patch_port, PatchPortAlreadyPatchedException, \
    edit_switch_port, remove_patch_to_patch_port, delete_switch_port
from pycroft.model.facilities import Room
from web.blueprints.infrastructure.forms import SwitchForm, SwitchPortForm

from pycroft.helpers import net
from pycroft.model import session
from pycroft.model.host import Switch, SwitchPort
from pycroft.model.net import VLAN, Subnet
from pycroft.model.port import PatchPort
from pycroft.lib.net import get_subnets_with_usage
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


def format_address_range(base_address, amount):
    if amount == 0:
        raise ValueError
    elif abs(amount) == 1:
        return str(base_address)
    elif amount > 1:
        return '{} - {}'.format(str(base_address),
                                str(base_address + amount - 1))
    else:
        return '{} - {}'.format(str(base_address + amount + 1),
                                str(base_address))


def format_reserved_addresses(subnet):
    reserved = []
    if subnet.reserved_addresses_bottom:
        reserved.append(
            format_address_range(subnet.address.network + 1,
                                 subnet.reserved_addresses_bottom))
    if subnet.reserved_addresses_top:
        reserved.append(
            format_address_range(subnet.address.broadcast - 1,
                                 -subnet.reserved_addresses_top))
    return reserved


@bp.route('/subnets/json')
def subnets_json():
    subnets_list = get_subnets_with_usage()
    return jsonify(items=[{
            'id': subnet.id,
            'description': subnet.description,
            'address': str(subnet.address),
            'gateway': str(subnet.gateway),
            'reserved': format_reserved_addresses(subnet),
            'free_ips': '{}'.format(subnet.max_ips - subnet.used_ips),
            'free_ips_formatted': '{} (von {})'.format(
                subnet.max_ips - subnet.used_ips,
                subnet.max_ips),
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
                'title': switch.host.name,
                'href': url_for(".switch_show", switch_id=switch.host_id)
            },
            'ip': str(switch.management_ip),
            "edit_link": {"href": url_for(".switch_edit", switch_id=switch.host_id),
                          'title': "Bearbeiten",
                          'icon': 'glyphicon-pencil',
                          'btn-class': 'btn-link'},
            "delete_link": {"href": url_for(".switch_delete", switch_id=switch.host_id),
                            'title': "Löschen",
                            'icon': 'glyphicon-trash',
                            'btn-class': 'btn-link'},
        } for switch in Switch.q.all()])


@bp.route('/switch/show/<int:switch_id>')
def switch_show(switch_id):
    switch = Switch.q.get(switch_id)
    if not switch:
        flash(u"Switch mit ID {} nicht gefunden!".format(switch_id), "error")
        return redirect(url_for('.switches'))
    return render_template(
        'infrastructure/switch_show.html',
        page_title=u"Switch: " + switch.host.name,
        switch=switch,
        port_table=PortTable(
            data_url=url_for('.switch_show_json', switch_id=switch.host_id),
            switch_id=switch_id))


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
            "switchport_name": port.name,
            "patchport_name": port.patch_port.name if port.patch_port else None,
            "room": {
                "href": url_for(
                    "facilities.room_show",
                    room_id=port.patch_port.room.id
                ),
                "title": port.patch_port.room.short_name
            } if port.patch_port else None,
            "edit_link": {"href": url_for(".switch_port_edit", switch_id=switch.host.id, switch_port_id=port.id),
                          'title': "Bearbeiten",
                          'icon': 'glyphicon-pencil',
                          'btn-class': 'btn-link'},
            "delete_link": {"href": url_for(".switch_port_delete", switch_id=switch.host.id, switch_port_id=port.id),
                            'title': "Löschen",
                            'icon': 'glyphicon-trash',
                            'btn-class': 'btn-link'},
        } for port in switch_port_list])


@bp.route('/switch/create', methods=['GET', 'POST'])
@access.require('infrastructure_change')
def switch_create():
    form = SwitchForm()

    if form.validate_on_submit():
        room = Room.q.filter_by(number=form.room_number.data,
                                level=form.level.data, building=form.building.data).one()

        switch = create_switch(form.name.data, IPAddress(form.management_ip.data), room, current_user)

        session.session.commit()

        flash("Die Switch wurde erfolgreich erstellt.", "success")

        return redirect(url_for('.switch_show', switch_id=switch.host_id))

    form_args = {
        'form': form,
        'cancel_to': url_for('.switches')
    }

    return render_template('generic_form.html',
                           page_title="Switch erstellen",
                           form_args=form_args)


@bp.route('/switch/<int:switch_id>/edit', methods=['GET', 'POST'])
@access.require('infrastructure_change')
def switch_edit(switch_id):
    switch = Switch.q.filter_by(host_id=switch_id).one()

    if not switch:
        flash(u"Switch mit ID {} nicht gefunden!".format(switch_id), "error")
        return redirect(url_for('.switches'))

    form = SwitchForm(name=switch.host.name, management_ip=switch.management_ip, building=switch.host.room.building,
                      level=switch.host.room.level, room_number=switch.host.room.number)

    if form.validate_on_submit():
        room = Room.q.filter_by(number=form.room_number.data,
                                level=form.level.data, building=form.building.data).one()

        edit_switch(switch, form.name.data, form.management_ip.data, room, current_user)

        session.session.commit()

        flash("Die Switch wurde erfolgreich bearbeitet.", "success")

        return redirect(url_for('.switches'))

    form_args = {
        'form': form,
        'cancel_to': url_for('.switches')
    }

    return render_template('generic_form.html',
                           page_title="Switch bearbeiten",
                           form_args=form_args)


@bp.route('/switch/<int:switch_id>/delete', methods=['GET', 'POST'])
@access.require('infrastructure_change')
def switch_delete(switch_id):
    switch = Switch.q.filter_by(host_id=switch_id).one()

    if not switch:
        flash(u"Switch mit ID {} nicht gefunden!".format(switch_id), "error")
        return redirect(url_for('.switches'))

    form = Form()

    if form.validate_on_submit():
        delete_switch(switch, current_user)

        session.session.commit()

        flash("Die Switch wurde erfolgreich gelöscht.", "success")

        return redirect(url_for('.switches'))

    form_args = {
        'form': form,
        'cancel_to': url_for('.switches'),
        'submit_text': 'Löschen',
        'actions_offset': 0
    }

    return render_template('generic_form.html',
                           page_title="Switch löschen",
                           form_args=form_args)


@bp.route('/switch/<int:switch_id>/port/create', methods=['GET', 'POST'])
@access.require('infrastructure_change')
def switch_port_create(switch_id):
    switch = Switch.q.get(switch_id)

    if not switch:
        flash(u"Switch mit ID {} nicht gefunden!".format(switch_id), "error")
        return redirect(url_for('.switches'))

    form = SwitchPortForm()

    form.patch_port.query = PatchPort.q.filter_by(switch_room=switch.host.room)

    if not form.is_submitted():
        form.default_vlans.process_data([VLAN.q.filter_by(name=switch.host.room.building.short_name).first()])

    if form.validate_on_submit():
        error = False

        switch_port = create_switch_port(switch, form.name.data, form.default_vlans.data, current_user)

        if form.patch_port.data:
            try:
                patch_switch_port_to_patch_port(switch_port, form.patch_port.data, current_user)
            except PatchPortAlreadyPatchedException:
                form.patch_port.errors.append("Dieser Patch-Port ist bereits mit einem Switch-Port verbunden.")
                error = True

        if not error:
            session.session.commit()

            flash("Der Switch-Port {} wurde erfolgreich erstellt.".format(switch_port.name), "success")

            return redirect(url_for('.switch_show', switch_id=switch.host_id))
        else:
            session.session.rollback()

    form_args = {
        'form': form,
        'cancel_to': url_for('.switch_show', switch_id=switch_id)
    }

    return render_template('generic_form.html',
                           page_title="Switch-Port erstellen",
                           form_args=form_args)


@bp.route('/switch/<int:switch_id>/port/<int:switch_port_id>/edit', methods=['GET', 'POST'])
@access.require('infrastructure_change')
def switch_port_edit(switch_id, switch_port_id):
    switch = Switch.q.get(switch_id)
    switch_port = SwitchPort.q.get(switch_port_id)

    if not switch:
        flash(u"Switch mit ID {} nicht gefunden!".format(switch_id), "error")
        return redirect(url_for('.switches'))

    if not switch_port:
        flash(u"SwitchPort mit ID {} nicht gefunden!".format(switch_port_id), "error")
        return redirect(url_for('.switch_show', switch_id=switch_id))

    if switch_port.switch != switch:
        flash(u"SwitchPort mit ID {} gehört nicht zu {}!".format(switch_port_id, switch.host.name), "error")
        return redirect(url_for('.switch_show', switch_id=switch_id))

    form = SwitchPortForm(obj=switch_port)

    form.patch_port.query = PatchPort.q.filter_by(switch_room=switch.host.room).order_by(PatchPort.name.asc())

    if form.validate_on_submit():
        error = False

        edit_switch_port(switch_port, form.name.data, form.default_vlans.data, current_user)

        if switch_port.patch_port != form.patch_port.data:
            if switch_port.patch_port:
                remove_patch_to_patch_port(switch_port.patch_port, current_user)

            if form.patch_port.data:
                try:
                    patch_switch_port_to_patch_port(switch_port, form.patch_port.data, current_user)
                except PatchPortAlreadyPatchedException:
                    form.patch_port.errors.append("Dieser Patch-Port ist bereits mit einem Switch-Port verbunden.")
                    error = True

        if not error:
            session.session.commit()

            flash("Der Switch-Port wurde erfolgreich bearbeitet.", "success")

            return redirect(url_for('.switch_show', switch_id=switch_port.switch_id))
        else:
            session.session.rollback()

    form_args = {
        'form': form,
        'cancel_to': url_for('.switch_show', switch_id=switch_port.switch_id)
    }

    return render_template('generic_form.html',
                           page_title="Switch-Port bearbeiten",
                           form_args=form_args)


@bp.route('/switch/<int:switch_id>/port/<int:switch_port_id>/delete', methods=['GET', 'POST'])
@access.require('infrastructure_change')
def switch_port_delete(switch_id, switch_port_id):
    switch = Switch.q.get(switch_id)
    switch_port = SwitchPort.q.get(switch_port_id)

    if not switch:
        flash(u"Switch mit ID {} nicht gefunden!".format(switch_id), "error")
        return redirect(url_for('.switches'))

    if not switch_port:
        flash(u"SwitchPort mit ID {} nicht gefunden!".format(switch_port_id), "error")
        return redirect(url_for('.switch_show', switch_id=switch_id))

    if switch_port.switch != switch:
        flash(u"SwitchPort mit ID {} gehört nicht zu {}!".format(switch_port_id, switch.host.name), "error")
        return redirect(url_for('.switch_show', switch_id=switch_id))

    form = Form()

    if form.validate_on_submit():
        delete_switch_port(switch_port, current_user)

        session.session.commit()

        flash("Der Switch-Port wurde erfolgreich gelöscht.", "success")

        return redirect(url_for('.switch_show', switch_id=switch_port.switch_id))

    form_args = {
        'form': form,
        'cancel_to': url_for('.switch_show', switch_id=switch_port.switch_id),
        'submit_text': 'Löschen',
        'actions_offset': 0
    }

    return render_template('generic_form.html',
                           page_title="Switch-Port löschen",
                           form_args=form_args)


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
