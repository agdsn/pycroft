from flask import url_for, flash, abort
from flask_login import current_user

from pycroft.lib.user import status
from pycroft.model.user import User


def user_btn_style(user):
    """Determine the icons and style of the button to a users page.

    First, add glyphicons concerning status warnings (finance,
    traffic, no network access, abuse), or an ok icon.  Append the
    admin icon (always) and the “has an LDAP-account” icon (only if
    not a member anymore).

    The button class is ``info`` for non-members, ``success`` for
    members, ``warning`` for traffic, and ``danger`` for other
    felonies.

    :param s: A user's status dict

    :return: The bootstrap glyphicon classes and the button class
    :rtype: tuple(list(str),str)
    """
    glyphicons = []
    btn_class = None
    tooltips = []
    props = set(p.property_name for p in user.current_properties)

    if 'network_access' not in props:
        glyphicons.append('glyphicon-remove')
        tooltips.append('Zugang gesperrt')

    if 'payment_in_default' in props:
        glyphicons.append('glyphicon-euro')
        btn_class = 'btn-warning'
        tooltips.append('nicht bezahlt')

    if 'member' in props:
        if 'traffic_limit_exceeded' in props:
            glyphicons.append('glyphicon-stats')
            btn_class = 'btn-warning'
            tooltips.append('Traffic')
        if 'violation' in props:
            glyphicons.append('glyphicon-alert')
            btn_class = 'btn-danger'
            tooltips.append('Verstoß')
    else:
        btn_class = 'btn-info'
        tooltips.append('Kein Mitglied')

    glyphicons = glyphicons or ['glyphicon-ok']
    btn_class = btn_class or 'btn-success'

    if 'user_show' in props:
        glyphicons.append('glyphicon-wrench')
        tooltips.append('Admin')

    if 'member' not in props and 'ldap' in props:
        glyphicons.append('glyphicon-cloud')
        tooltips.append('Eintrag im LDAP')

    tooltip = ', '.join(tooltips)

    return btn_class, glyphicons, tooltip


def user_button(user):
    btn_class, glyphicons, tooltip = user_btn_style(user)
    return {
        'href': url_for("user.user_show", user_id=user.id),
        'title': user.name,
        'icon': glyphicons,
        'btn_class': btn_class,
        'tooltip': tooltip
    }


def get_user_or_404(user_id):
    user = User.q.get(user_id)
    if user is None:
        flash(u"Nutzer mit ID {} existiert nicht!".format(user_id,), 'error')
        abort(404)
    return user


def no_membership_change():
    return not current_user.has_property('groups_change_membership')


def no_hosts_change():
    return not current_user.has_property('hosts_change')
