# -*- coding: utf-8 -*-
"""
    web.blueprints.infrastructure
    ~~~~~~~~~~~~~~

    This module defines view functions for /infrastructure

    :copyright: (c) 2012 by AG DSN.
"""

from flask import Blueprint, flash, redirect, render_template, url_for
from pycroft.helpers import host
from pycroft.model.host import Switch, Host
from pycroft.model.dormitory import Subnet, VLAN
from pycroft.model.dns import Record, CNameRecord
from web.blueprints.navigation import BlueprintNavigation
from web.blueprints.infrastructure.forms import SwitchPortForm
from web.blueprints.infrastructure.forms import CNameRecordEditForm
from web.blueprints.infrastructure.forms import CNameRecordCreateForm
from web.blueprints.infrastructure.forms import RecordCreateForm
from web.blueprints.infrastructure.forms import a_records_query
from web.blueprints.access import BlueprintAccess

from pycroft.lib.dns import delete_record, change_record, create_cname_record
from pycroft.lib.infrastructure import create_switch_port

bp = Blueprint('infrastructure', __name__, )
access = BlueprintAccess(bp, ['infrastructure_show'])
nav = BlueprintNavigation(bp, "Infrastruktur", blueprint_access=access)


@bp.route('/subnets')
@nav.navigate(u"Subnetze")
@access.require('infrastructure_show')
def subnets():
    subnets_list = Subnet.q.all()
    return render_template('infrastructure/subnets_list.html',
        subnets = subnets_list)


@bp.route('/switches')
@nav.navigate(u"Switche")
@access.require('infrastructure_show')
def switches():
    switches_list = Switch.q.all()
    return render_template('infrastructure/switches_list.html',
        switches=switches_list)


@bp.route('/user/<int:user_id>/record_delete/<int:record_id>')
@access.require('infrastructure_change')
def record_delete(user_id, record_id):
    delete_record(record_id)
    flash(u"Record gelöscht", 'success')

    return redirect(url_for("user.user_show", user_id=user_id))


@bp.route('/user/<int:user_id>/record_edit/<int:record_id>',
    methods=['GET', 'POST'])
@access.require('infrastructure_change')
def record_edit(user_id, record_id):
    record = Record.q.get(record_id)

    edit_function = ".%s_edit" % (record.discriminator,)

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
    record = CNameRecord.q.get(record_id)

    form = CNameRecordEditForm()
    form.record_for.data = record.record_for.name

    if form.validate_on_submit():
        change_record(record, name=form.name.data)

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
        form.type.data = 'CNameRecord'

    if form.validate_on_submit():
        create_function = ".%s_create" % (form.type.data,)

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
    form = CNameRecordCreateForm()
    form.record_for.query = a_records_query(host_id)
    host = Host.q.get(host_id)

    if form.validate_on_submit():
        create_cname_record(host=host, name=form.name.data,
            record_for=form.record_for.data)

        flash(u"Neuer CNameRecord angelegt", 'success')

        return redirect(url_for("user.user_show", user_id=user_id))

    return render_template('infrastructure/recordtype_create.html', form=form,
        user_id=user_id, host_id=host_id,
        page_title=u"Neuen CNameRecord erzeugen")


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
def switch_show(switch_id):
    switch = Switch.q.get(switch_id)
    if not switch:
        flash(u"Switch mit ID %s nicht gefunden!" % switch_id, "error")
        return redirect(url_for('.switches'))
    switch_port_list = switch.ports
    switch_port_list = host.sort_ports(switch_port_list)
    return render_template('infrastructure/switch_show.html',
        page_title=u"Switch: " + switch.name,
        switch=switch, switch_ports=switch_port_list)


@bp.route('/switch/<int:switch_id>/switch_port/create', methods=['GET', 'POST'])
@access.require('infrastructure_change')
def switch_port_create(switch_id):
    form = SwitchPortForm()
    switch = Switch.q.get(switch_id)
    if form.validate_on_submit():
        create_switch_port(name=form.name.data, switch_id=switch_id)
        flash(u'Neuer Switch Port angelegt', 'success')
        return redirect(url_for('.switch_show', switch_id=switch_id))
    return render_template('infrastructure/switch_port_create.html',
        form=form, switch_id=switch_id,
        page_title=u"Neuer Switch Port für " + switch.name)


@bp.route('/vlans')
@nav.navigate(u"VLANs")
@access.require('infrastructure_show')
def vlans():
    vlans_list = VLAN.q.all()
    return render_template('infrastructure/vlan_list.html',
                           vlans=vlans_list)
