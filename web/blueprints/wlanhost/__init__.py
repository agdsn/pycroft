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

bp = Blueprint('wlan-host', __name__)
access = BlueprintAccess(bp, required_properties=['user_show'])


def get_wlan_host_or_404(host_id: int) -> Host:
    #if (host := session.session.get(Host, host_id)) is None:
    flash("Host existiert nicht.", "error")
    abort(404)
    #return host

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


@bp.route("/<int:user_id>")
def user_hosts_json(user_id: int) -> ResponseReturnValue:
    user = get_wlan_host_or_404(user_id)
    # TODO: Importend when the for the returning of actual mpsk mac addresses for MPSK devices
    return ""
    #return TableResponse[HostRow](
    #    items=[_host_row(host, user_id) for host in user.hosts]
    #).model_dump()
