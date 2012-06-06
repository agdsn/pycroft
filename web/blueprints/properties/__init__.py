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
from pycroft.model.properties import PropertyGroup, TrafficGroup
from pycroft.model.session import session

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
        new_traffic_group = TrafficGroup(name=form.name.data,
            traffic_limit=int(form.traffic_limit.data)*1024*1024*1024)
        session.add(new_traffic_group)
        session.commit()
        flash('Traffic Gruppe angelegt', 'success')
        return redirect(url_for('.traffic_groups'))
    return render_template('properties/traffic_group_create.html', form=form,
    page_title = u"Neue Traffic Gruppe")


@bp.route('/traffic_group/delete/<traffic_group_id>')
def traffic_group_delete(traffic_group_id):
    traffic_group = TrafficGroup.q.get(traffic_group_id)
    session.delete(traffic_group)
    #TODO remove memberships with this group, too!
    session.commit()
    flash('Traffic Group gelöscht', 'success')
    return redirect(url_for('.traffic_groups'))


@bp.route('/property_groups')
@nav.navigate(u"Eigenschaften Gruppen")
def property_groups():
    return render_template('properties/base.html')


@bp.route('/property_group/create')
def property_group_create():
    return render_template('properties/base.html',
        page_title = u"Neue Eigenschaften Gruppe")


@bp.route('/properties')
@nav.navigate(u"Eigenschaften")
def rights():
    return render_template('properties/base.html')
