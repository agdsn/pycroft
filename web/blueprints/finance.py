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

bp = Blueprint('finance', __name__, )


@bp.route('/')
@bp.route('/journals')
def journals():
    return render_template('finance/finance_base.html', page_title = u"Journals")


@bp.route('/accounts')
def accounts():
    return render_template('finance/finance_base.html', page_title = u"Konten")


@bp.route('/transactions')
def transactions():
    return render_template('finance/finance_base.html', page_title = u"Transaktionen")


