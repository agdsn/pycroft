from flask import url_for

from pycroft.lib.user import status


def userstatus_btn_style(s):
    """Determine the icons and style of the button to a users page.

    First, add glyphicons concerning status warnings (finance,
    traffic, no network access, abuse), or an ok icon.  Append admin
    and mail-only icons.

    The button class is ``info`` for non-members, ``success`` for
    members, ``warning`` for traffic, and ``danger`` for other
    felonies.

    :param s: A user's status dict

    :return: The bootstrap glyphicon classes and the button class
    :rtype: tuple(list(str),str)
    """
    glyphicons = []
    btn_class = None

    if not s.account_balanced:
        glyphicons.append('glyphicon-euro')
        btn_class = 'btn-warning'

    if s.member:
        if s.traffic_exceeded:
            glyphicons.append('glyphicon-stats')
            btn_class = 'btn-warning'
        if not s.network_access:
            glyphicons.append('glyphicon-remove')
            btn_class = 'btn-danger'
        if s.violation:
            glyphicons.append('glyphicon-alert')
            btn_class = 'btn-danger'
    else:
        btn_class = 'btn-info'

    glyphicons = glyphicons or ['glyphicon-ok']
    btn_class = btn_class or 'btn-success'

    if s.admin:
        glyphicons.append('glyphicon-wrench')

    if not s.member and s.mail:
        glyphicons.append('glyphicon-envelope')

    return btn_class, glyphicons


def user_button(user, user_status=None):
    user_status = user_status or status(user)
    btn_class, glyphicons = userstatus_btn_style(user_status)
    return {
        'href': url_for("user.user_show", user_id=user.id),
        'title': user.name,
        'icon': glyphicons,
        'btn_class': btn_class
    }
