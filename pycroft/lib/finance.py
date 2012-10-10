# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
__author__ = 'Florian Österreich'

from pycroft.model.finance import Semester, FinanceAccount
from pycroft.model import session

def semester_create(name, registration_fee, semester_fee, begin_date, end_date):
    """
    This function creates a new Semester.
    There are created a registration fee account and a semester fee account
    which ones are attached to the semester
    The name could be something like: "Wintersemester 2012/13"
    :param name: A usefull name for the semester.
    :param registration_fee: The fee a student have to pay when he moves in first.
    :param semester_fee: The fee a student have to pay every semester.
    :param begin_date: Date when the semester starts.
    :param end_date: Date when semester ends.
    :return: The created Semester.
    """
    new_semester = Semester(name=name,
        registration_fee=registration_fee,
        semester_fee=semester_fee,
        begin_date=begin_date,
        end_date=end_date)

    new_registration_fee_account = FinanceAccount("Anmeldegebühr %s" % name)

    new_semester_fee_account = FinanceAccount("Semestergebühr %s" % name)

    session.session.add(new_registration_fee_account)
    session.session.add(new_semester_fee_account)
    session.session.add(new_semester)
    session.session.commit()
    return new_semester
