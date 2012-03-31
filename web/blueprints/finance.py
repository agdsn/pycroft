# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    web.blueprints.finance
    ~~~~~~~~~~~~~~

    This module defines view functions for /finance

    :copyright: (c) 2012 by AG DSN.
"""

from flask import Blueprint, render_template
from web import app

bp = Blueprint('bp_finance', __name__, )


@bp.route('/finance')
@bp.route('/finance/journals')
def finance_journals():
    return render_template('test.html', page_title = u"Journals", subnav = 'nav/finance.html')


@bp.route('/finance/accounts')
def finance_accounts():
    return render_template('test.html', page_title = u"Konten", subnav = 'nav/finance.html')


@bp.route('/finance/transactions')
def finance_transactions():
    return render_template('test.html', page_title = u"Transaktionen", subnav = 'nav/finance.html')


app.register_blueprint(bp)
