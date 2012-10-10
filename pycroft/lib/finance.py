# -*- coding: utf-8 -*-
__author__ = 'Florian Österreich'

from pycroft.model.finance import Semester
from pycroft.model import session

def semester_create(name, registration_fee, semester_fee, begin_date, end_date):
    """
    This function creates a new Semester.
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
    session.session.add(new_semester)
    session.session.commit()
    return new_semester