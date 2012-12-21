# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    web.blueprints.infrastructure
    ~~~~~~~~~~~~~~

    This module defines view functions for /infrastructure

    :copyright: (c) 2012 by AG DSN.
"""

from flask import Blueprint, flash, redirect, render_template, url_for
from pycroft.helpers import host
from pycroft.model.host import Switch
from pycroft.model.host_alias import HostAlias, CNameRecord
from web.blueprints.navigation import BlueprintNavigation
from web.blueprints.infrastructure.forms import SwitchPortForm
from web.blueprints.infrastructure.forms import CNameRecordEditForm
from web.blueprints.infrastructure.forms import CNameRecordCreateForm
from web.blueprints.infrastructure.forms import RecordCreateForm
from web.blueprints.infrastructure.forms import arecords_query

from pycroft.lib.host_alias import delete_alias, change_alias, create_cnamerecord
from pycroft.lib.infrastructure import create_switch_port

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


@bp.route('/user/<int:user_id>/record_delete/<int:alias_id>')
def record_delete(user_id, alias_id):
    delete_alias(alias_id)
    flash(u"Record gelöscht", 'success')

    return redirect(url_for("user.user_show", user_id=user_id))


@bp.route('/user/<int:user_id>/record_edit/<int:alias_id>',
    methods=['GET', 'POST'])
def record_edit(user_id, alias_id):
    alias = HostAlias.q.get(alias_id)

    edit_function = ".%s_edit" % (alias.discriminator,)

    return redirect(
        url_for(edit_function, user_id=user_id, alias_id=alias_id))


@bp.route('/user/<int:user_id>/record_edit/<int:alias_id>/a')
def arecord_edit(user_id, alias_id):
    return redirect(url_for("user.user_show", user_id=user_id))


@bp.route('/user/<int:user_id>/record_edit/<int:alias_id>/aaaa')
def aaaarecord_edit(user_id, alias_id):
    return redirect(url_for("user.user_show", user_id=user_id))


@bp.route('/user/<int:user_id>/record_edit/<int:alias_id>/cname',
    methods=['GET', 'POST'])
def cnamerecord_edit(user_id, alias_id):
    alias = CNameRecord.q.get(alias_id)

    form = CNameRecordEditForm()
    form.alias_for.data = alias.alias_for.name

    if form.validate_on_submit():
        change_alias(alias, name=form.name.data)

        flash(u"Alias geändert", "success")
        return redirect(url_for("user.user_show", user_id=user_id))

    return render_template('infrastructure/record_edit.html',
        form=form, user_id=user_id,
        page_title=u"Alias ändern für " + alias.alias_for.name)


@bp.route('/user/<int:user_id>/record_edit/<int:alias_id>/mx')
def mxrecord_edit(user_id, alias_id):
    return redirect(url_for("user.user_show", user_id=user_id))


@bp.route('/user/<int:user_id>/record_edit/<int:alias_id>/ns')
def nsrecord_edit(user_id, alias_id):
    return redirect(url_for("user.user_show", user_id=user_id))


@bp.route('/user/<int:user_id>/record_edit/<int:alias_id>/srv')
def srvrecord_edit(user_id, alias_id):
    return redirect(url_for("user.user_show", user_id=user_id))


@bp.route('/user/<int:user_id>/record_create/<int:host_id>',
    methods=['GET', 'POST'])
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
        page_title=u"Alias erzeugen")


@bp.route('/user/<int:user_id>/record_create/<int:host_id>/a')
def arecord_create(user_id, host_id):
    return redirect(url_for("user.user_show", user_id=user_id))


@bp.route('/user/<int:user_id>/record_create/<int:host_id>/aaaa')
def aaaarecord_create(user_id, host_id):
    return redirect(url_for("user.user_show", user_id=user_id))


@bp.route('/user/<int:user_id>/record_create/<int:host_id>/cname',
    methods=['GET', 'POST'])
def cnamerecord_create(user_id, host_id):
    form = CNameRecordCreateForm()
    form.alias_for.query = arecords_query(host_id)

    if form.validate_on_submit():
        create_cnamerecord(host_id=host_id, name=form.name.data,
            alias_for=form.alias_for.data)

        flash(u"Neuer CNameRecord angelegt", 'success')

        return redirect(url_for("user.user_show", user_id=user_id))

    return render_template('infrastructure/recordtype_create.html', form=form,
        user_id=user_id, host_id=host_id,
        page_title=u"Neuen CNameRecord erzeugen")


@bp.route('/user/<int:user_id>/record_create/<int:host_id>/mx')
def mxrecord_create(user_id, host_id):
    return redirect(url_for("user.user_show", user_id=user_id))


@bp.route('/user/<int:user_id>/record_create/<int:host_id>/ns')
def nsrecord_create(user_id, host_id):
    return redirect(url_for("user.user_show", user_id=user_id))


@bp.route('/user/<int:user_id>/record_create/<int:host_id>/srv')
def srvrecord_create(user_id, host_id):
    return redirect(url_for("user.user_show", user_id=user_id))


@bp.route('/switch/show/<switch_id>')
def switch_show(switch_id):
    switch = Switch.q.get(switch_id)
    switch_port_list = switch.ports
    switch_port_list = host.sort_ports(switch_port_list)
    return render_template('infrastructure/switch_show.html',
        page_title=u"Switch: " + switch.name,
        switch=switch, switch_ports=switch_port_list)


@bp.route('/switch/<switch_id>/switch_port/create', methods=['GET', 'POST'])
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
@nav.navigate(u"Vlans")
def vlans():
    return render_template('infrastructure/base.html')
