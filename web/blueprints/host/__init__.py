import re
import traceback

from flask import Blueprint, flash, abort, redirect, url_for, render_template, \
    jsonify, request
from flask_login import current_user
from flask_wtf import FlaskForm
from ipaddr import IPv4Address

from pycroft.helpers.net import mac_regex, get_interface_manufacturer
from pycroft.lib import host as lib_host
from pycroft.lib.net import get_subnets_for_room, get_unused_ips, \
    MacExistsException
from pycroft.model import session
from pycroft.model.facilities import Room
from pycroft.model.host import Host, Interface, MulticastFlagException
from pycroft.model.user import User
from web.blueprints.access import BlueprintAccess
from web.blueprints.helpers.exception import web_execute
from web.blueprints.helpers.form import refill_room_data
from web.blueprints.helpers.host import validate_unique_mac
from web.blueprints.helpers.user import get_user_or_404
from web.blueprints.host.forms import InterfaceForm, HostForm
from web.blueprints.host.tables import InterfaceTable

bp = Blueprint('host', __name__)
access = BlueprintAccess(bp, required_properties=['user_show'])


@bp.route('/<int:host_id>/delete', methods=['GET', 'POST'])
@access.require('hosts_change')
def host_delete(host_id):
    host = Host.q.get(host_id)

    if host is None:
        flash(u"Host existiert nicht.", 'error')
        abort(404)

    form = FlaskForm()

    owner = host.owner

    if form.is_submitted():
        _, success = web_execute(lib_host.host_delete,
                                 "Host erfolgreich gelöscht.",
                                 host, current_user)

        if success:
            session.session.commit()

            return redirect(url_for('user.user_show', user_id=owner.id,
                                    _anchor='hosts'))

    form_args = {
        'form': form,
        'cancel_to': url_for('user.user_show', user_id=owner.id),
        'submit_text': 'Löschen',
        'actions_offset': 0
    }

    return render_template('generic_form.html',
                           page_title="Host löschen",
                           form_args=form_args,
                           form=form)


@bp.route('/<int:host_id>/edit', methods=['GET', 'POST'])
@access.require('hosts_change')
def host_edit(host_id):
    host = Host.q.get(host_id)

    if host is None:
        flash(u"Host existiert nicht.", 'error')
        abort(404)

    form = HostForm(obj=host)

    if not form.is_submitted():
        refill_room_data(form, host.room)

    if form.validate_on_submit():
        room = Room.q.filter_by(number=form.room_number.data,
                                level=form.level.data,
                                building=form.building.data).one()

        owner = User.q.filter_by(id=form.owner_id.data).one()

        _, success = web_execute(lib_host.host_edit,
                                 "Host erfolgreich bearbeitet.",
                                 host, owner, room, form.name.data,
                                 current_user)

        if success:
            session.session.commit()

            return redirect(url_for('user.user_show', user_id=owner.id,
                                    _anchor='hosts'))

    form_args = {
        'form': form,
        'cancel_to': url_for('user.user_show', user_id=host.owner.id)
    }

    return render_template('generic_form.html',
                           page_title="Host editieren",
                           form_args=form_args,
                           form=form)


@bp.route('/create', methods=['GET', 'POST'])
@access.require('hosts_change')
def host_create():
    user = get_user_or_404(request.args.get('user_id', None))

    form = HostForm(owner_id=user.id)

    if not form.is_submitted():
        refill_room_data(form, user.room)

    if form.validate_on_submit():
        room = Room.q.filter_by(number=form.room_number.data,
                                level=form.level.data,
                                building=form.building.data).one()

        owner = User.q.filter_by(id=form.owner_id.data).one()

        host, success = web_execute(lib_host.host_create,
                                    "Host erfolgreich erstellt.",
                                    owner, room, form.name.data, current_user)

        if success:
            session.session.commit()

            return redirect(
                url_for('user.interface_create', user_id=host.owner_id,
                        host_id=host.id,
                        _anchor='hosts'))

    form_args = {
        'form': form,
        'cancel_to': url_for('user.user_show', user_id=user.id)
    }

    return render_template('generic_form.html',
                           page_title="Host erstellen",
                           form_args=form_args,
                           form=form)


@bp.route("/<int:host_id>/interfaces")
def host_interfaces_json(host_id):
    host = Host.q.get(host_id)

    if host is None:
        flash(u"Host existiert nicht.", 'error')
        abort(404)

    interfaces = []

    for interface in host.interfaces:
        interfaces.append({
            'id': interface.id,
            'host': host.name,
            'name': interface.name,
            'ips': ', '.join(str(ip.address) for ip in interface.ips),
            'mac': interface.mac,
            'actions': [
                {
                    'href': url_for('.interface_edit',
                                    interface_id=interface.id),
                    'title': "Bearbeiten",
                    'icon': 'glyphicon-pencil',
                    'btn-class': 'btn-link'},
                {'href': url_for('.interface_delete',
                                 interface_id=interface.id),
                 'title': "Löschen",
                 'icon': 'glyphicon-trash',
                 'btn-class': 'btn-link'}
            ]
        })

    return jsonify(items=interfaces)


@bp.route("/<int:host_id>/interfaces/table")
def interface_table(host_id):
    return render_template('host/interface_table.html',
                           interface_table=InterfaceTable(
                               data_url=url_for(".host_interfaces_json",
                                                host_id=host_id),
                               host_id=host_id),
                           host_id=host_id)


@bp.route('/interface/<int:interface_id>/delete', methods=['GET', 'POST'])
@access.require('hosts_change')
def interface_delete(interface_id):
    interface = Interface.q.get(interface_id)

    if interface is None:
        flash(u"Interface existiert nicht.", 'error')
        abort(404)

    form = FlaskForm()

    if form.is_submitted():
        _, success = web_execute(lib_host.interface_delete,
                                 "Interface erfolgreich gelöscht.",
                                 interface, current_user)

        if success:
            session.session.commit()

            return redirect(
                url_for('user.user_show', user_id=interface.host.owner_id,
                        _anchor='hosts'))

    form_args = {
        'form': form,
        'cancel_to': url_for('user.user_show', user_id=interface.host.owner_id),
        'submit_text': 'Löschen',
        'actions_offset': 0
    }

    return render_template('generic_form.html',
                           page_title="Interface löschen",
                           form_args=form_args,
                           form=form)


@bp.route('/interface/<int:interface_id>/edit', methods=['GET', 'POST'])
@access.require('hosts_change')
def interface_edit(interface_id):
    interface = Interface.q.get(interface_id)

    if interface is None:
        flash(u"Interface existiert nicht.", 'error')
        abort(404)

    subnets = get_subnets_for_room(interface.host.room)

    current_ips = list(ip.address for ip in interface.ips)

    form = InterfaceForm(obj=interface)

    unused_ips = [ip for ips in get_unused_ips(subnets).values() for ip in ips]

    form.ips.choices = [(str(ip), str(ip)) for ip in current_ips + unused_ips]

    unique_mac_error = None

    if not form.is_submitted():
        form.ips.process_data(ip for ip in current_ips)
    else:
        if form.mac.data != interface.mac:
            unique_mac_error = validate_unique_mac(form, form.mac)

            if unique_mac_error:
                form.validate()

                form.mac.errors.append(unique_mac_error)

    if not unique_mac_error and form.validate_on_submit():
        ips = set([IPv4Address(ip) for ip in form.ips.data])

        _, success = web_execute(lib_host.interface_edit,
                                 "Interface erfolgreich bearbeitet.",
                                 interface,
                                 form.name.data,
                                 form.mac.data,
                                 ips,
                                 current_user
                                 )

        if success:
            session.session.commit()

            return redirect(
                url_for('user.user_show', user_id=interface.host.owner_id,
                        _anchor='hosts'))

    form_args = {
        'form': form,
        'cancel_to': url_for('user.user_show', user_id=interface.host.owner_id)
    }

    return render_template('generic_form.html',
                           page_title="Interface editieren",
                           form_args=form_args)


@bp.route('/<int:host_id>/interface/create', methods=['GET', 'POST'])
@access.require('hosts_change')
def interface_create(host_id):
    host = Host.q.get(host_id)

    if host is None:
        flash(u"Host existiert nicht.", 'error')
        abort(404)

    subnets = get_subnets_for_room(host.room)

    form = InterfaceForm()

    unused_ips = [ip for ips in get_unused_ips(subnets).values() for ip in ips]

    form.ips.choices = [(str(ip), str(ip)) for ip in unused_ips]

    unique_mac_error = None

    if not form.is_submitted():
        form.ips.process_data([next(iter(unused_ips), None)])
    else:
        unique_mac_error = validate_unique_mac(form, form.mac)

        if unique_mac_error:
            form.validate()

            form.mac.errors.append(unique_mac_error)

    if not unique_mac_error and form.validate_on_submit():
        ips = set([IPv4Address(ip) for ip in form.ips.data])

        _, success = web_execute(lib_host.interface_create,
                                 "Interface erfolgreich erstellt.",
                                 host,
                                 form.name.data,
                                 form.mac.data,
                                 ips,
                                 current_user
                                 )

        if success:
            session.session.commit()

            return redirect(url_for('user.user_show', user_id=host.owner.id,
                                    _anchor='hosts'))

    form_args = {
        'form': form,
        'cancel_to': url_for('user.user_show', user_id=host.owner.id)
    }

    return render_template('generic_form.html',
                           page_title="Interface erstellen",
                           form_args=form_args)


@bp.route("/<int:user_id>")
def user_hosts_json(user_id):
    user = get_user_or_404(user_id)

    list_items = []
    for host in user.hosts:
        if host.room:
            patch_ports = host.room.connected_patch_ports
            switches = ', '.join(
                p.switch_port.switch.host.name for p in patch_ports)
            ports = ', '.join(p.switch_port.name for p in patch_ports)
        else:
            switches = None
            ports = None

        list_items.append({
            'id': host.id,
            'name': host.name,
            'switch': switches,
            'port': ports,
            'actions': [{'href': url_for('.host_edit', host_id=host.id,
                                         user_id=user_id),
                         'title': "Bearbeiten",
                         'icon': 'glyphicon-pencil',
                         'btn-class': 'btn-link'},
                        {'href': url_for('.host_delete', host_id=host.id),
                         'title': "Löschen",
                         'icon': 'glyphicon-trash',
                         'btn-class': 'btn-link'}],
            'interfaces_table_link': url_for('.interface_table',
                                             host_id=host.id),
            'interface_create_link': url_for('.interface_create',
                                             host_id=host.id),
        })
    return jsonify(items=list_items)


@bp.route("/interface-manufacturer/<string:mac>")
def interface_manufacturer_json(mac):
    if not re.match(mac_regex, mac):
        return abort(400)

    return jsonify(manufacturer=get_interface_manufacturer(mac))
