# -*- coding: utf-8 -*-
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
from web.blueprints.access import BlueprintAccess

bp = Blueprint('properties', __name__, )
access = BlueprintAccess(bp, ['groups_traffic_show', 'groups_show'])
nav = BlueprintNavigation(bp, "Eigenschaften", blueprint_access=access)


@bp.route('/traffic_groups')
@nav.navigate(u"Trafficgruppen")
@access.require('groups_traffic_show')
def traffic_groups():
    traffic_groups_list = TrafficGroup.q.all()
    return render_template('properties/traffic_groups_list.html',
        traffic_groups=traffic_groups_list)


@bp.route('/traffic_group/create', methods=['GET', 'POST'])
@access.require('groups_traffic_change')
def traffic_group_create():
    form = TrafficGroupForm()
    if form.validate_on_submit():
        # traffic limit in byte per seven days
        group = create_traffic_group(name=form.name.data,
            traffic_limit=int(form.traffic_limit.data)*1024*1024*1024)
        message = u'Traffic Gruppe {0} angelegt'
        flash(message.format(group.name), 'success')
        return redirect(url_for('.traffic_groups'))
    return render_template('properties/traffic_group_create.html', form=form,
    page_title = u"Neue Traffic Gruppe")


@bp.route('/traffic_group/<group_id>/delete')
@access.require('groups_traffic_change')
def traffic_group_delete(group_id):
    group = delete_traffic_group(group_id)
    message = u'Traffic Gruppe {0} gelöscht'
    flash(message.format(group.name), 'success')
    return redirect(url_for('.traffic_groups'))


@bp.route('/property_groups')
@access.require('groups_show')
@nav.navigate(u"Eigenschaftsgruppen")
def property_groups():
    property_groups_list = PropertyGroup.q.all()
    return render_template('properties/property_groups_list.html',
        property_categories = property_categories,
        property_groups=property_groups_list,
        num_groups = len(property_groups_list))


@bp.route('/property_group/create', methods=['GET', 'POST'])
@access.require('groups_change')
def property_group_create():
    form = PropertyGroupForm()
    if form.validate_on_submit():
        group = create_property_group(name=form.name.data)
        message = u'Eigenschaften Gruppe {0} angelegt.'
        flash(message.format(group.name), 'success')
        return redirect(url_for('.property_groups'))
    return render_template('properties/property_group_create.html', form=form,
        page_title = u"Neue Eigenschaften Gruppe")


@bp.route('/property_group/<group_id>/add/<property_name>')
@access.require('groups_change')
def property_group_add_property(group_id, property_name):
    property_group = PropertyGroup.q.get(group_id)
    (group, property) = create_property(name=property_name,
        property_group= property_group, granted=True)
    message = u'Eigenschaft {0} zur Gruppe {1} hinzugefügt.'
    flash(message.format(property.name, group.name), 'success')
    return redirect(url_for('.property_groups'))


@bp.route('/property_group/<group_id>/delete/<property_name>')
@access.require('groups_change')
def property_group_delete_property(group_id, property_name):
    (group, property) = delete_property(group_id, property_name)
    message = u'Eigenschaft {0} von Gruppe {1} entfernt'
    flash(message.format(property.name, group.name), 'success')
    return redirect(url_for('.property_groups'))


@bp.route('/property_group/<group_id>/delete')
@access.require('groups_change')
def property_group_delete(group_id):
    group = delete_property_group(group_id)
    message = u'Eigenschaften Gruppe {0} gelöscht'
    flash(message.format(group.name), 'success')
    return redirect(url_for('.property_groups'))
