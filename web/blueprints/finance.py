# -*- coding: utf-8 -*-
"""
    web.blueprints.finance
    ~~~~~~~~~~~~~~

    This module defines view functions for /finance

    :copyright: (c) 2012 by AG DSN.
"""

from flask import Blueprint, render_template

bp = Blueprint('bp_finance', __name__, )


@bp.route('/')
@bp.route('/journals')
def journals():
    return render_template('test.html', page_title = u"Journals", subnav = 'nav/finance.html')


@bp.route('/accounts')
def accounts():
    return render_template('test.html', page_title = u"Konten", subnav = 'nav/finance.html')


@bp.route('/transactions')
def transactions():
    return render_template('test.html', page_title = u"Transaktionen", subnav = 'nav/finance.html')


