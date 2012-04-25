# -*- coding: utf-8 -*-
"""
    web.blueprints.user.helpers
    ~~~~~~~~~~~~~~

    This module provides the following helpers for /user:
    - password generator
    - getRegex checker

    :copyright: (c) 2012 by AG DSN.
"""

import random

def generatePassword(length):
    allowedLetters = "abcdefghijklmnopqrstuvwxyz!$%&()=.," \
        ":;-_#+1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    passwordLength = length
    password = ""
    for i in range(passwordLength):
        password += allowedLetters[random.choice(range(len
            (allowedLetters)))]
    return password


def getRegex(type):
    regexName = "^(([a-z]{1,5}|[A-Z][a-z0-9]+)\\s)*([A-Z][a-z0-9]+)((-|\\s)"\
                "[A-Z][a-z0-9]+|\\s[a-z]{1,5})*$"
    regexLogin = "^[a-z][a-z0-9_]{1,20}[a-z0-9]$"
    regexMac = "^[a-f0-9]{2}(:[a-f0-9]{2}){5}$"
    regexRoom = "^[0-9]{1,6}$"

    if type == "name":
        return regexName
    if type == "login":
        return regexLogin
    if type == "mac":
        return regexMac
    if type == "room":
        return regexRoom