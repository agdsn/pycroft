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

from flask import Blueprint, flash, jsonify, redirect, render_template, url_for, abort

from pycroft.model import session
from pycroft.property import property_categories
from pycroft.model.user import Property, PropertyGroup
from pycroft.lib.membership import grant_property, deny_property, \
    remove_property
from web.blueprints.access import BlueprintAccess
from web.blueprints.navigation import BlueprintNavigation
from web.blueprints.properties.forms import PropertyGroupForm

bp = Blueprint('properties', __name__)
access = BlueprintAccess(bp, required_properties=['groups_show'])
nav = BlueprintNavigation(bp, "Einstellungen", blueprint_access=access)


@bp.route('/property_groups')
@nav.navigate(u"Gruppen")
def property_groups():
    property_groups_list = PropertyGroup.q.all()
    categories = property_categories
    properties_with_description = set(chain(*(
        category.keys() for category in categories.values()
    )))
    properties = set(property_name[0] for property_name
                     in Property.q.distinct().values(Property.name))
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
        session.session.add(group)
        session.session.commit()
        message = u'Eigenschaftengruppe {0} angelegt.'
        flash(message.format(group.name), 'success')
        return redirect(url_for('.property_groups'))
    return render_template('properties/property_group_create.html', form=form,
        page_title = u"Neue Eigenschaftengruppe")


@bp.route('/property_group/<group_id>/grant/<property_name>')
@access.require('groups_change')
def property_group_grant_property(group_id, property_name):
    property_group = PropertyGroup.q.get(group_id)

    if property_group is None:
        flash(u"Eigenschaftengruppe mit ID {} existiert nicht!".format(group_id), 'error')
        abort(404)

    grant_property(property_group, property_name)
    session.session.commit()
    message = u'Eigenschaft {0} der Gruppe {1} gewährt.'
    flash(message.format(property_name, property_group.name), 'success')
    return redirect(url_for('.property_groups'))


@bp.route('/property_group/<group_id>/deny/<property_name>')
@access.require('groups_change')
def property_group_deny_property(group_id, property_name):
    property_group = PropertyGroup.q.get(group_id)

    if property_group is None:
        flash(u"Eigenschaftengruppe mit ID {} existiert nicht!".format(group_id), 'error')
        abort(404)

    deny_property(property_group, property_name)
    session.session.commit()
    message = u'Eigenschaft {0} der Gruppe {1} verboten.'
    flash(message.format(property_name, property_group.name), 'success')
    return redirect(url_for('.property_groups'))


@bp.route('/property_group/<group_id>/remove/<property_name>')
@access.require('groups_change')
def property_group_remove_property(group_id, property_name):
    group = PropertyGroup.q.get(group_id)

    if group is None:
        flash(u"Eigenschaftengruppe mit ID {} existiert nicht!".format(group_id), 'error')
        abort(404)

    remove_property(group, property_name)
    session.session.commit()
    message = u'Eigenschaft {0} der Gruppe {1} entfernt.'
    flash(message.format(property_name, group.name), 'success')
    return redirect(url_for('.property_groups'))


@bp.route('/property_group/<group_id>/delete')
@access.require('groups_change')
def property_group_delete(group_id):
    group = PropertyGroup.q.get(group_id)

    if group is None:
        flash(u"Eigenschaftengruppe mit ID {} existiert nicht!".format(group_id), 'error')
        abort(404)

    session.session.delete(group)
    session.session.commit()
    message = u'Eigenschaftengruppe {0} gelöscht'
    flash(message.format(group.name), 'success')
    return redirect(url_for('.property_groups'))


@bp.route('/json/propertygroups')
def json_propertygroups():
    groups = [(entry.id, entry.name) for entry in PropertyGroup.q.all()]

    return jsonify(dict(items=groups))

