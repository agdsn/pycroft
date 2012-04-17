# -*- coding: utf-8 -*-
"""
    web.blueprints.user
    ~~~~~~~~~~~~~~

    This module defines view functions for /user

    :copyright: (c) 2012 by AG DSN.
"""

from flask import Blueprint, render_template, flash
from web.blueprints import BlueprintNavigation
from pycroft.model import dormitory

bp = Blueprint('user', __name__, )
nav = BlueprintNavigation(bp, "Nutzer")


def sort_key(dormitory):
    key = 0
    power = 1
    for char in reversed(dormitory.number.lower()):
        key += ord(char) * pow(10, power)
        power += power

    return key

@bp.route('/')
@nav.navigate(u"Übersicht")
def overview():
    dormitories_list = dormitory.Dormitory.q.all()
    dormitories_list = sorted(dormitories_list,
        key=lambda dormitory: sort_key(dormitory))

    return render_template('user/overview.html',
        dormitories=dormitories_list)

@bp.route('/dormitory/<dormitory_id>')
def dormitory_floors(dormitory_id):
    floors_list = ["dummy 1","dummy 2", "dummy 3"]
    return render_template('user/floors.html',
        floors=floors_list, page_title=u"Etagen Wohnheim XY")

@bp.route('/create')
@nav.navigate("Anlegen")
def create():
    flash("Test1", "info")
    flash("Test2", "warning")
    flash("Test3", "error")
    flash("Test4", "success")
    return render_template('user/base.html')


@bp.route('/search')
@nav.navigate("Suchen")
def search():
    return render_template('user/base.html')
