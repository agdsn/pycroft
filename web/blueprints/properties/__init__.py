# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    web.blueprints.properties
    ~~~~~~~~~~~~~~

    This module defines view functions for /properties

    :copyright: (c) 2012 by AG DSN.
"""

from flask import Blueprint, flash, redirect, render_template, url_for
from web.blueprints.navigation import BlueprintNavigation
from web.blueprints.properties.forms import PropertyGroupForm, TrafficGroupForm
from pycroft.model.property import PropertyGroup, TrafficGroup, \
    property_categories
from pycroft.lib.property import delete_property, delete_property_group, \
    delete_traffic_group, create_property, create_property_group, \
    create_traffic_group

bp = Blueprint('properties', __name__, )
nav = BlueprintNavigation(bp, "Eigenschaften")


@bp.route('/traffic_groups')
@nav.navigate(u"Traffic Gruppen")
def traffic_groups():
    traffic_groups_list = TrafficGroup.q.all()
    return render_template('properties/traffic_groups_list.html',
        traffic_groups=traffic_groups_list)


@bp.route('/traffic_group/create', methods=['GET', 'POST'])
def traffic_group_create():
    form = TrafficGroupForm()
    if form.validate_on_submit():
        # traffic limit in byte per seven days
        group = create_traffic_group(name=form.name.data,
            traffic_limit=int(form.traffic_limit.data)*1024*1024*1024)
        flash(u'Traffic Gruppe {} angelegt'.format(group.name), 'success')
        return redirect(url_for('.traffic_groups'))
    return render_template('properties/traffic_group_create.html', form=form,
    page_title = u"Neue Traffic Gruppe")


@bp.route('/traffic_group/<group_id>/delete')
def traffic_group_delete(group_id):
    group = delete_traffic_group(group_id)
    flash(u'Traffic Gruppe {} gelöscht'.format(group.name), 'success')
    return redirect(url_for('.traffic_groups'))


@bp.route('/property_groups')
@nav.navigate(u"Eigenschaften Gruppen")
def property_groups():
    property_groups_list = PropertyGroup.q.all()
    return render_template('properties/property_groups_list.html',
        property_categories = property_categories,
        property_groups=property_groups_list,
        num_groups = len(property_groups_list))


@bp.route('/property_group/create', methods=['GET', 'POST'])
def property_group_create():
    form = PropertyGroupForm()
    if form.validate_on_submit():
        group = create_property_group(name=form.name.data)
        flash(u'Eigenschaften Gruppe {} angelegt'.format(group.name), 'success')
        return redirect(url_for('.property_groups'))
    return render_template('properties/property_group_create.html', form=form,
        page_title = u"Neue Eigenschaften Gruppe")


@bp.route('/property_group/<group_id>/add/<property_name>')
def property_group_add_property(group_id, property_name):
    (group, property) = create_property(group_id=group_id, name=property_name,
        property_group_id= group_id)
    flash(u'Eigenschaft {} zur Gruppe {} hinzugefügt'.format(property.name,
        group.name), 'success')
    return redirect(url_for('.property_groups'))


@bp.route('/property_group/<group_id>/delete/<property_name>')
def property_group_delete_property(group_id, property_name):
    (group, property) = delete_property(group_id, property_name)
    flash(u'Eigenschaft {} von Gruppe {} entfernt'.format(property.name,
        group.name), 'success')
    return redirect(url_for('.property_groups'))


@bp.route('/property_group/<group_id>/delete')
def property_group_delete(group_id):
    group = delete_property_group(group_id)
    flash(u'Eigenschaften Gruppe {} gelöscht'.format(group.name), 'success')
    return redirect(url_for('.property_groups'))
