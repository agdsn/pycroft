# -*- coding: utf-8 -*-
"""
    pycroft.helpers.dormitory_helper
    ~~~~~~~~~~~~~~

    :copyright: (c) 2012 by AG DSN.
"""
import re


def sort_dormitories(dormitories):
    number_re = re.compile(r"[0-9]+")
    letter_re = re.compile(r"[a-z]")

    def make_sort_key(dormitory):
        number = number_re.search(dormitory.number)
        letter = letter_re.search(dormitory.number.lower())

        if letter:
            return ord(letter.group(0)) + 256 * int(number.group(0))

        return 256 * int(number.group(0))

    sorted_dormitories = sorted(dormitories, key=make_sort_key)

    return sorted_dormitories
