# -*- coding: utf-8 -*-
# Copyright (c) 2013 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
__author__ = 'Florian Österreich'

from pycroft.model.finance import Semester, FinanceAccount
from pycroft.model import session
from pycroft.lib import config

def create_semester(name, registration_fee, semester_fee, begin_date, end_date):
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
    semester = Semester(name=name,
        registration_fee=registration_fee,
        semester_fee=semester_fee,
        begin_date=begin_date,
        end_date=end_date)

    objects = [semester]
    for account in config.get("finance")["semester_accounts"]:
        objects.append(FinanceAccount(type=account["type"],name=account["name"],semester=semester,tag=account["tag"]))

    session.session.add_all(objects)
    session.session.commit()
    return semester
