import re

from flask import Blueprint, flash, abort, redirect, url_for, render_template, request
from flask.typing import ResponseReturnValue
from flask_login import current_user
from flask_wtf import FlaskForm
from netaddr import IPAddress

from pycroft.exc import PycroftException
from pycroft.helpers.net import mac_regex, get_interface_manufacturer
from pycroft.lib import mpsk_client as lib_mpsk
from pycroft.lib.net import get_subnets_for_room
from pycroft.lib.facilities import get_room
from pycroft.model import session
from pycroft.model.host import Host, Interface
from pycroft.model.mpsk_client import MPSKClient
from pycroft.model.user import User
from web.blueprints.access import BlueprintAccess
from web.blueprints.helpers.exception import abort_on_error
from web.blueprints.helpers.form import refill_room_data
from web.blueprints.helpers.user import get_user_or_404
from web.blueprints.host.forms import InterfaceForm, HostForm
from web.blueprints.host.tables import InterfaceTable, HostTable, HostRow, InterfaceRow
from web.blueprints.mpskclient.forms import WiFiInterfaceForm
from web.blueprints.mpskclient.tables import MPSKRow
from web.table.table import TableResponse, BtnColResponse, LinkColResponse

bp = Blueprint("wifi-mpsk", __name__)
access = BlueprintAccess(bp, required_properties=["user_show"])


def get_mpsk_client_or_404(mpsk_id: int) -> MPSKClient:
    if (mpsk := session.session.get(MPSKClient, mpsk_id)) is None:
        flash("Host existiert nicht.", "error")
        abort(404)
    return mpsk


@bp.route("/create", methods=["GET", "POST"])
@access.require("hosts_change")
def host_create() -> ResponseReturnValue:
    user = get_user_or_404(request.args.get("user_id", default=None, type=int))
    form = WiFiInterfaceForm(owner_id=user.id)

    def default_response() -> ResponseReturnValue:
        form_args = {"form": form, "cancel_to": url_for("user.user_show", user_id=user.id)}

        return render_template(
            "generic_form.html", page_title="MPSK Client erstellen", form_args=form_args, form=form
        )

    if not form.is_submitted():
        return default_response()
        refill_room_data(form, user.room)

    if not form.validate_on_submit():
        return default_response()

    # existence verified by validator
    # TODO can't we provide an attribute for that on the form?
    owner = session.session.get(User, form.owner_id.data)
    with abort_on_error(default_response), session.session.begin_nested():
        host = lib_mpsk.mpsk_client_create(
            session.session, owner, form.name.data, form.mac.data, processor=current_user
        )
    session.session.commit()

    flash("MPSK Client erfolgreich erstellt.", "success")
    return redirect(url_for("user.user_show", user_id=host.owner.id, _anchor="mpsks"))


@bp.route("/<int:mpsk_id>/delete", methods=["GET", "POST"])
@access.require("hosts_change")
def mpsk_delete(mpsk_id: int) -> ResponseReturnValue:
    mpsk = get_mpsk_client_or_404(mpsk_id)
    owner = mpsk.owner
    form = FlaskForm()

    def default_response() -> ResponseReturnValue:
        form_args = {
            "form": form,
            "cancel_to": url_for("user.user_show", user_id=owner.id),
            "submit_text": "Löschen",
            "actions_offset": 0,
        }

        return render_template(
            "generic_form.html", page_title="MPSK Client löschen", form_args=form_args, form=form
        )

    if not form.is_submitted():
        return default_response()

    with abort_on_error(default_response), session.session.begin_nested():
        lib_mpsk.mpsk_delete(session.session, mpsk, current_user)
    session.session.commit()

    flash("MPSK Client erfolgreich gelöscht.", "success")
    return redirect(url_for("user.user_show", user_id=owner.id, _anchor="mpsks"))


@bp.route("/<int:mpsk_id>/edit", methods=["GET", "POST"])
@access.require("hosts_change")
def mpsk_edit(mpsk_id: int) -> ResponseReturnValue:
    mpsk = get_mpsk_client_or_404(mpsk_id)

    form = WiFiInterfaceForm(obj=mpsk)

    def default_response() -> ResponseReturnValue:
        form_args = {"form": form, "cancel_to": url_for("user.user_show", user_id=mpsk.owner_id)}

        return render_template(
            "generic_form.html", page_title="MPSK Client editieren", form_args=form_args
        )

    if not form.is_submitted() or not form.validate():
        return default_response()

    with abort_on_error(default_response), session.session.begin_nested():
        lib_mpsk.mpsk_edit(
            session.session, mpsk, mpsk.owner, form.name.data, form.mac.data, current_user
        )
    session.session.add(mpsk)
    session.session.commit()
    flash("MPSK Client erfolgreich bearbeitet.", "success")
    return redirect(url_for("user.user_show", user_id=mpsk.owner_id, _anchor="mpsks"))


@bp.route("/<int:user_id>")
def user_clients_json(user_id: int) -> ResponseReturnValue:
    user = get_user_or_404(user_id)
    # TODO: Importend when the for the returning of actual mpsk mac addresses for MPSK devices
    # return ""
    return TableResponse[MPSKRow](
        items=[_mpsk_row(mpsk, user_id) for mpsk in user.mpsks]
    ).model_dump()


def _mpsk_row(client: MPSKClient, user_id: int) -> MPSKRow:
    return MPSKRow(
        id=client.id,
        name=client.name,
        mac=client.mac,
        actions=[
            BtnColResponse(
                href=url_for(".mpsk_edit", mpsk_id=client.id),
                title="Bearbeiten",
                icon="fa-edit",
                btn_class="btn-link",
            ),
            BtnColResponse(
                href=url_for(".mpsk_delete", mpsk_id=client.id),
                title="Löschen",
                icon="fa-trash",
                btn_class="btn-link",
            ),
        ],
    )
