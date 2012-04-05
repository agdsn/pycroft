# -*- coding: utf-8 -*-
"""
    web.blueprints.finance
    ~~~~~~~~~~~~~~

    This module defines view functions for /finance

    :copyright: (c) 2012 by AG DSN.
"""

from flask import Blueprint, render_template
from web.blueprints import BlueprintNavigation

bp = Blueprint('finance', __name__, )
nav = BlueprintNavigation(bp, "Finanzen")


@bp.route('/')
@bp.route('/journals')
@nav.navigate(u"Journale")
def journals():
    return render_template('finance/finance_base.html', page_title = u"Journals")


@bp.route('/accounts')
@nav.navigate(u"Konten")
def accounts():
    return render_template('finance/finance_base.html', page_title = u"Konten")


@bp.route('/transactions')
@nav.navigate(u"Transaktionen")
def transactions():
    return render_template('finance/finance_base.html', page_title = u"Transaktionen")


