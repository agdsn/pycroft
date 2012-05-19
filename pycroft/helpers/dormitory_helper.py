# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    pycroft.helpers.dormitory_helper
    ~~~~~~~~~~~~~~

    :copyright: (c) 2012 by AG DSN.
"""
import re

def sort_dormitory_key(dormitory):
    number = re.search("[0-9]+", dormitory.number)
    letter = re.search("[a-z]", dormitory.number.lower())

    if letter:
        return ord(letter.group(0)) + 256*int(number.group(0))

    return 256*int(number.group(0))


def sort_dormitories(dormitories):
    sorted_dormitories = sorted(dormitories,
        key=lambda dormitory: sort_dormitory_key(dormitory))

    return sorted_dormitories
