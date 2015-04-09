# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    web.blueprints.properties
    ~~~~~~~~~~~~~~

    This module defines view functions for /properties

    :copyright: (c) 2012 by AG DSN.
"""
from itertools import chain
import operator

from flask import Blueprint, flash, redirect, render_template, url_for
from flask.json import jsonify
from pycroft._compat import itervalues, iterkeys, imap

from pycroft.model import session
from pycroft.property import property_categories
from pycroft.model.user import Property, PropertyGroup, TrafficGroup
from pycroft.lib.user import grant_property, deny_property, remove_property
from web.blueprints.access import BlueprintAccess
from web.blueprints.navigation import BlueprintNavigation
from web.blueprints.properties.forms import PropertyGroupForm, TrafficGroupForm
from web.template_filters import byte_size_filter


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


@bp.route('/traffic_groups/json')
@access.require('groups_traffic_show')
def traffic_groups_json():
    return jsonify(items=[{
            'name': group.name,
            'limit': byte_size_filter(group.traffic_limit),
            'delete': {
                'href': url_for(".traffic_group_delete", group_id=group.id),
                'title': 'Löschen',
                'btn_class': '',
                'glyphicon': 'glyphicon-delete'
            }
        } for group in TrafficGroup.q.all()])


@bp.route('/traffic_group/create', methods=['GET', 'POST'])
@access.require('groups_traffic_change')
def traffic_group_create():
    form = TrafficGroupForm()
    if form.validate_on_submit():
        # traffic limit in byte per seven days
        group = TrafficGroup(
            name=form.name.data,
            traffic_limit=int(form.traffic_limit.data)*1024*1024*1024)
        session.session.add(group)
        session.session.commit()
        message = u'Traffic Gruppe {0} angelegt'
        flash(message.format(group.name), 'success')
        return redirect(url_for('.traffic_groups'))
    return render_template('properties/traffic_group_create.html', form=form,
    page_title = u"Neue Traffic Gruppe")


@bp.route('/traffic_group/<group_id>/delete')
@access.require('groups_traffic_change')
def traffic_group_delete(group_id):
    group = TrafficGroup.q.get(group_id)
    session.session.delete(group)
    session.session.commit()
    message = u'Traffic Gruppe {0} gelöscht'
    flash(message.format(group.name), 'success')
    return redirect(url_for('.traffic_groups'))


@bp.route('/property_groups')
@access.require('groups_show')
@nav.navigate(u"Eigenschaftsgruppen")
def property_groups():
    property_groups_list = PropertyGroup.q.all()
    categories = property_categories
    properties_with_description = set(chain(*(
        iterkeys(category) for category in itervalues(categories)
    )))
    properties = set(imap(
        operator.itemgetter(0),
        Property.q.distinct().values(Property.name)))
    categories[u"Ohne Beschreibung"] = {
        p: p for p in properties if p not in properties_with_description
    }
    return render_template(
        'properties/property_groups_list.html',
        property_categories=property_categories,
        property_groups=property_groups_list
    )


@bp.route('/property_group/create', methods=['GET', 'POST'])
@access.require('groups_change')
def property_group_create():
    form = PropertyGroupForm()
    if form.validate_on_submit():
        group = PropertyGroup(name=form.name.data)
        session.session.commit()
        message = u'Eigenschaften Gruppe {0} angelegt.'
        flash(message.format(group.name), 'success')
        return redirect(url_for('.property_groups'))
    return render_template('properties/property_group_create.html', form=form,
        page_title = u"Neue Eigenschaften Gruppe")


@bp.route('/property_group/<group_id>/grant/<property_name>')
@access.require('groups_change')
def property_group_grant_property(group_id, property_name):
    property_group = PropertyGroup.q.get(group_id)
    grant_property(property_group, property_name)
    session.session.commit()
    message = u'Eigenschaft {0} der Gruppe {1} gewährt.'
    flash(message.format(property_name, property_group.name), 'success')
    return redirect(url_for('.property_groups'))


@bp.route('/property_group/<group_id>/deny/<property_name>')
@access.require('groups_change')
def property_group_deny_property(group_id, property_name):
    property_group = PropertyGroup.q.get(group_id)
    deny_property(property_group, property_name)
    session.session.commit()
    message = u'Eigenschaft {0} der Gruppe {1} verboten.'
    flash(message.format(property_name, property_group.name), 'success')
    return redirect(url_for('.property_groups'))


@bp.route('/property_group/<group_id>/remove/<property_name>')
@access.require('groups_change')
def property_group_remove_property(group_id, property_name):
    group = PropertyGroup.q.get(group_id)
    remove_property(group, property_name)
    session.session.commit()
    message = u'Eigenschaft {0} der Gruppe {1} entfernt.'
    flash(message.format(property_name, group.name), 'success')
    return redirect(url_for('.property_groups'))


@bp.route('/property_group/<group_id>/delete')
@access.require('groups_change')
def property_group_delete(group_id):
    group = PropertyGroup.q.get(group_id)
    session.session.delete(group)
    session.session.commit()
    message = u'Eigenschaften Gruppe {0} gelöscht'
    flash(message.format(group.name), 'success')
    return redirect(url_for('.property_groups'))
