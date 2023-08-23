# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    web.blueprints.properties
    ~~~~~~~~~~~~~~

    This module defines view functions for /properties

    :copyright: (c) 2012 by AG DSN.
"""
import typing as t
from collections import OrderedDict
from itertools import chain

from flask import Blueprint, flash, redirect, render_template, url_for, abort
from flask.typing import ResponseValue
from flask_login import current_user
from flask_wtf import FlaskForm

from pycroft.lib.membership import grant_property, deny_property, \
    remove_property, edit_property_group, delete_property_group, \
    known_properties
from pycroft.model import session
from pycroft.model.user import PropertyGroup
from pycroft.property import property_categories
from web.blueprints.access import BlueprintAccess
from web.blueprints.navigation import BlueprintNavigation
from web.blueprints.properties.forms import PropertyGroupForm

bp = Blueprint('properties', __name__)
access = BlueprintAccess(bp, required_properties=['groups_show'])
nav = BlueprintNavigation(bp, "", icon='fa-cogs', push_right=True, blueprint_access=access)


@bp.route('/property_groups')
@nav.navigate("Gruppen")
def property_groups() -> ResponseValue:
    property_groups_list = PropertyGroup.q.all()
    categories = property_categories
    properties_with_description = set(
        chain(*(category.keys() for category in categories.values()))
    )
    categories["Ohne Beschreibung"] = OrderedDict(
        {
            p: p
            for p in sorted(known_properties())
            if p not in properties_with_description
        }
    )
    return render_template(
        'properties/property_groups_list.html',
        property_categories=property_categories,
        property_groups=property_groups_list
    )


@bp.route('/property_group/create', methods=['GET', 'POST'])
@access.require('groups_change')
def property_group_create() -> ResponseValue:
    form = PropertyGroupForm()
    if form.validate_on_submit():
        group = PropertyGroup(name=form.name.data,
                              permission_level=form.permission_level.data)
        session.session.add(group)
        session.session.commit()
        message = 'Eigenschaftengruppe {0} angelegt.'
        flash(message.format(group.name), 'success')
        return redirect(url_for('.property_groups'))
    return render_template('properties/property_group_create.html', form=form,
        page_title = "Neue Eigenschaftengruppe")


@bp.route('/property_group/<group_id>/grant/<property_name>')
@access.require('groups_change')
def property_group_grant_property(group_id, property_name) -> ResponseValue:
    property_group = session.session.get(PropertyGroup, group_id)

    if property_group is None:
        flash(f"Eigenschaftengruppe mit ID {group_id} existiert nicht!", 'error')
        abort(404)

    grant_property(property_group, property_name)
    session.session.commit()
    message = 'Eigenschaft {0} der Gruppe {1} gewährt.'
    flash(message.format(property_name, property_group.name), 'success')
    return redirect(url_for('.property_groups'))


@bp.route('/property_group/<group_id>/deny/<property_name>')
@access.require('groups_change')
def property_group_deny_property(group_id, property_name) -> ResponseValue:
    property_group = session.session.get(PropertyGroup, group_id)

    if property_group is None:
        flash(f"Eigenschaftengruppe mit ID {group_id} existiert nicht!", 'error')
        abort(404)

    deny_property(property_group, property_name)
    session.session.commit()
    message = 'Eigenschaft {0} der Gruppe {1} verboten.'
    flash(message.format(property_name, property_group.name), 'success')
    return redirect(url_for('.property_groups'))


@bp.route('/property_group/<group_id>/remove/<property_name>')
@access.require('groups_change')
def property_group_remove_property(group_id, property_name) -> ResponseValue:
    group = session.session.get(PropertyGroup, group_id)

    if group is None:
        flash(f"Eigenschaftengruppe mit ID {group_id} existiert nicht!", 'error')
        abort(404)

    remove_property(group, property_name)
    session.session.commit()
    message = 'Eigenschaft {0} der Gruppe {1} entfernt.'
    flash(message.format(property_name, group.name), 'success')
    return redirect(url_for('.property_groups'))


@bp.route('/property_group/<group_id>/edit', methods=['GET', 'POST'])
@access.require('groups_change')
def property_group_edit(group_id) -> ResponseValue:
    group = session.session.get(PropertyGroup, group_id)

    if group is None:
        flash(f"Eigenschaftengruppe mit ID {group_id} existiert nicht!", 'error')
        abort(404)

    form = PropertyGroupForm(obj=group)

    if form.is_submitted():
        edit_property_group(group, form.name.data, form.permission_level.data,
                            current_user)

        session.session.commit()

        flash('Eigenschaftsgruppe bearbeitet.', 'success')
        return redirect(url_for('.property_groups'))

    form_args = {
        'form': form,
        'cancel_to': url_for('.property_groups'),
        'submit_text': 'Speichern'
    }

    return render_template('generic_form.html',
                           page_title=f"Eigenschaftsgruppe '{group.name}' bearbeiten",
                           form_args=form_args,
                           form=form)


@bp.route('/property_group/<group_id>/delete', methods=['GET', 'POST'])
@access.require('groups_change')
def property_group_delete(group_id) -> ResponseValue:
    group = session.session.get(PropertyGroup, group_id)

    if group is None:
        flash(f"Eigenschaftengruppe mit ID {group_id} existiert nicht!", 'error')
        abort(404)

    form = FlaskForm()

    if form.is_submitted():
        delete_property_group(group, current_user)

        session.session.commit()

        flash('Eigenschaftsgruppe gelöscht.', 'success')
        return redirect(url_for('.property_groups'))

    form_args = {
        'form': form,
        'cancel_to': url_for('.property_groups'),
        'submit_text': 'Löschen',
        'actions_offset': 0
    }

    return render_template('generic_form.html',
                           page_title=f"Eigenschaftsgruppe '{group.name}' löschen",
                           form_args=form_args,
                           form=form)
