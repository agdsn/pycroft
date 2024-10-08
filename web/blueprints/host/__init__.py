import re

from flask import Blueprint, flash, abort, redirect, url_for, render_template, request
from flask.typing import ResponseReturnValue
from flask_login import current_user
from flask_wtf import FlaskForm
from netaddr import IPAddress

from pycroft.exc import PycroftException
from pycroft.helpers.net import mac_regex, get_interface_manufacturer
from pycroft.lib import host as lib_host
from pycroft.lib.net import get_subnets_for_room
from pycroft.lib.facilities import get_room
from pycroft.model import session
from pycroft.model.host import Host, Interface
from pycroft.model.user import User
from web.blueprints.access import BlueprintAccess
from web.blueprints.helpers.exception import abort_on_error
from web.blueprints.helpers.form import refill_room_data
from web.blueprints.helpers.user import get_user_or_404
from web.blueprints.host.forms import InterfaceForm, HostForm
from web.blueprints.host.tables import InterfaceTable, HostTable, HostRow, InterfaceRow
from web.table.table import TableResponse, BtnColResponse, LinkColResponse

bp = Blueprint('host', __name__)
access = BlueprintAccess(bp, required_properties=['user_show'])


def get_host_or_404(host_id: int) -> Host:
    if (host := session.session.get(Host, host_id)) is None:
        flash("Host existiert nicht.", "error")
        abort(404)
    return host

@bp.route('/<int:host_id>/delete', methods=['GET', 'POST'])
@access.require('hosts_change')
def host_delete(host_id: int) -> ResponseReturnValue:
    host = get_host_or_404(host_id)
    owner = host.owner
    form = FlaskForm()

    def default_response() -> ResponseReturnValue:
        form_args = {
            'form': form,
            'cancel_to': url_for('user.user_show', user_id=owner.id),
            'submit_text': 'Löschen',
            'actions_offset': 0
        }

        return render_template(
            'generic_form.html',
            page_title="Host löschen", form_args=form_args, form=form
        )

    if not form.is_submitted():
        return default_response()

    with abort_on_error(default_response), session.session.begin_nested():
        lib_host.host_delete(host, current_user)
    session.session.commit()

    flash("Host erfolgreich gelöscht.", 'success')
    return redirect(url_for('user.user_show', user_id=owner.id, _anchor='hosts'))


@bp.route('/<int:host_id>/edit', methods=['GET', 'POST'])
@access.require('hosts_change')
def host_edit(host_id: int) -> ResponseReturnValue:
    host = get_host_or_404(host_id)
    form = HostForm(obj=host)

    def default_response() -> ResponseReturnValue:
        form_args = {
            'form': form, 'cancel_to':
            url_for('user.user_show', user_id=host.owner.id)
        }
        return render_template(
            'generic_form.html',
            page_title="Host editieren", form_args=form_args, form=form
        )

    if not form.is_submitted():
        refill_room_data(form, host.room)
        return default_response()

    if not form.validate():
        return default_response()

    # existence guaranteed by validator
    owner = session.session.get(User, form.owner_id.data)
    with abort_on_error(default_response), session.session.begin_nested():
        if not (
            room := get_room(
                building_id=form.building.data.id,
                level=form.level.data,
                room_number=form.room_number.data,
            )
        ):
            form.room_number.errors.append("room does not exist")
            return default_response()
        lib_host.host_edit(host, owner, room, form.name.data, processor=current_user)
    session.session.commit()

    flash("Host erfolgreich bearbeitet.", 'success')
    return redirect(url_for(
        'user.user_show',
        user_id=owner.id, _anchor='hosts'
    ))


@bp.route('/create', methods=['GET', 'POST'])
@access.require('hosts_change')
def host_create() -> ResponseReturnValue:
    user = get_user_or_404(request.args.get("user_id", default=None, type=int))
    form = HostForm(owner_id=user.id)

    def default_response() -> ResponseReturnValue:
        form_args = {
            'form': form,
            'cancel_to': url_for('user.user_show', user_id=user.id)
        }

        return render_template(
            'generic_form.html',
            page_title="Host erstellen", form_args=form_args, form=form
        )
    if not form.is_submitted():
        refill_room_data(form, user.room)

    if not form.validate_on_submit():
        return default_response()

    # existence verified by validator
    # TODO can't we provide an attribute for that on the form?
    owner = session.session.get(User, form.owner_id.data)
    with abort_on_error(default_response), session.session.begin_nested():
        if not (
            room := get_room(
                # TODO I know this is a double query,
                # but we should fix this on the `get_room` side.
                building_id=form.building.data.id,
                level=form.level.data,
                room_number=form.room_number.data,
            )
        ):
            form.room_number.errors.append("room does not exist")
            return default_response()

        host = lib_host.host_create(owner, room, form.name.data, processor=current_user)
    session.session.commit()

    flash("Host erfolgreich erstellt.", "success")
    return redirect(
        url_for(
            ".interface_create", user_id=host.owner_id, host_id=host.id, _anchor="hosts"
        )
    )


@bp.route("/<int:host_id>/interfaces")
def host_interfaces_json(host_id: int) -> ResponseReturnValue:
    host = get_host_or_404(host_id)

    return TableResponse[InterfaceRow](
        items=[
            InterfaceRow(
                id=interface.id,
                host=host.name,
                name=interface.name,
                ips=", ".join(str(ip.address) for ip in interface.ips),
                mac=interface.mac,
                actions=[
                    BtnColResponse(
                        href=url_for(".interface_edit", interface_id=interface.id),
                        title="Bearbeiten",
                        icon="fa-edit",
                        btn_class="btn-link",
                    ),
                    BtnColResponse(
                        href=url_for(".interface_delete", interface_id=interface.id),
                        title="Löschen",
                        icon="fa-trash",
                        btn_class="btn-link",
                    ),
                ],
            )
            for interface in host.interfaces
        ]
    ).model_dump()


@bp.route("/<int:host_id>/interfaces/table")
def interface_table(host_id: int) -> ResponseReturnValue:
    return render_template('host/interface_table.html',
                           interface_table=InterfaceTable(
                               data_url=url_for(".host_interfaces_json",
                                                host_id=host_id),
                               host_id=host_id),
                           host_id=host_id)


def get_interface_or_404(id: int) -> Interface:
    if (interface := session.session.get(Interface, id)) is None:
        flash("Interface existiert nicht.", "error")
        abort(404)
    return interface


@bp.route('/interface/<int:interface_id>/delete', methods=['GET', 'POST'])
@access.require('hosts_change')
def interface_delete(interface_id: int) -> ResponseReturnValue:
    interface = get_interface_or_404(interface_id)

    form = FlaskForm()

    def default_response() -> ResponseReturnValue:
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

    if not form.is_submitted():
        return default_response()

    with abort_on_error(default_response), session.session.begin_nested():
        lib_host.interface_delete(interface, current_user)
    session.session.commit()

    flash("Interface erfolgreich gelöscht.", 'success')
    return redirect(url_for(
        'user.user_show',
        user_id=interface.host.owner_id, _anchor='hosts'
    ))


@bp.route('/interface/<int:interface_id>/edit', methods=['GET', 'POST'])
@access.require('hosts_change')
def interface_edit(interface_id: int) -> ResponseReturnValue:
    interface = get_interface_or_404(interface_id)

    subnets = get_subnets_for_room(interface.host.room)
    current_ips = [ip.address for ip in interface.ips]
    unused_ips = [ip for subnet in subnets for ip in subnet.unused_ips_iter()]

    form = InterfaceForm(obj=interface)
    form.meta.current_mac = interface.mac
    form.ips.choices = [(str(ip), str(ip)) for ip in current_ips + unused_ips]

    def default_response() -> ResponseReturnValue:
        form_args = {
            'form': form,
            'cancel_to': url_for('user.user_show', user_id=interface.host.owner_id)
        }

        return render_template('generic_form.html',
                               page_title="Interface editieren",
                               form_args=form_args)

    if not form.is_submitted():
        form.ips.process_data(ip for ip in current_ips)
        return default_response()
    if not form.validate():
        return default_response()

    ips = {IPAddress(ip) for ip in form.ips.data}

    with abort_on_error(default_response), session.session.begin_nested():
        lib_host.interface_edit(
            interface, form.name.data, form.mac.data, ips, processor=current_user
        )
    session.session.commit()

    flash("Interface erfolgreich bearbeitet.", 'success')
    return redirect(url_for('user.user_show', user_id=interface.host.owner_id, _anchor='hosts'))


@bp.route("/<int:host_id>/interface/create", methods=["GET", "POST"])
@access.require("hosts_change")
def interface_create(host_id: int) -> ResponseReturnValue:
    host = get_host_or_404(host_id)
    subnets = get_subnets_for_room(host.room)
    form = InterfaceForm()
    unused_ips = [ip for subnet in subnets for ip in subnet.unused_ips_iter()]
    form.ips.choices = [(str(ip), str(ip)) for ip in unused_ips]

    def default_response() -> ResponseReturnValue:
        form_args = {
            'form': form,
            'cancel_to': url_for('user.user_show', user_id=host.owner.id)
        }

        return render_template('generic_form.html',
                               page_title="Interface erstellen",
                               form_args=form_args)

    if not form.is_submitted():
        form.ips.process_data([next(iter(unused_ips), None)])
        return default_response()
    if not form.validate():
        return default_response()

    ips = {IPAddress(ip) for ip in form.ips.data}

    try:
        lib_host.interface_create(
            host,
            form.name.data,
            form.mac.data,
            ips,
            current_user
        )
        session.session.commit()
    except PycroftException:  # pragma: no cover
        return default_response()

    flash("Interface erfolgreich erstellt.", 'success')
    return redirect(url_for(
        'user.user_show',
        user_id=host.owner.id, _anchor='hosts'
    ))


def _host_row(host: Host, user_id: int) -> HostRow:
    if host.room:
        patch_ports = host.room.connected_patch_ports
        switches = [p.switch_port.switch.host for p in patch_ports]
        switch_links = [
            LinkColResponse(
                href=url_for("infrastructure.switch_show", switch_id=s.id),
                title=s.name or f"<unnamed switch #{s.id}>",
            )
            for s in switches
        ]
        ports = ", ".join(p.switch_port.name for p in patch_ports)
    else:
        switch_links = []
        ports = None
    return HostRow(
        id=host.id,
        name=host.name,
        switch=switch_links,
        port=ports,
        actions=[
            BtnColResponse(
                    href=url_for('.host_edit', host_id=host.id, user_id=user_id),
                    title="Bearbeiten",
                    icon='fa-edit',
                    btn_class='btn-link'
                ),
            BtnColResponse(
                href=url_for(".host_delete", host_id=host.id),
                title="Löschen",
                icon="fa-trash",
                btn_class="btn-link",
            ),
        ],
        interfaces_table_link=url_for(".interface_table", host_id=host.id),
        interface_create_link=url_for(".interface_create", host_id=host.id),
    )


@bp.route("/<int:user_id>")
def user_hosts_json(user_id: int) -> ResponseReturnValue:
    user = get_user_or_404(user_id)
    return TableResponse[HostRow](
        items=[_host_row(host, user_id) for host in user.hosts]
    ).model_dump()


@bp.route("/interface-manufacturer/<string:mac>")
def interface_manufacturer_json(mac: str) -> ResponseReturnValue:
    if not re.match(mac_regex, mac):
        return abort(400)
    return {"manufacturer": get_interface_manufacturer(mac)}
