# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
pycroft.helpers.errorcode
~~~~~~~~~~~~~~~~~~~~~~~~~
"""
import typing as t
from abc import ABCMeta, abstractmethod


def digits(n: int, base: int = 10) -> t.Iterator[int]:
    """
    Generate all digits of number in a given base starting with the least
    significant digit.

    :param n: An integral number
    :param base: Defaults to 10.
    """
    if base < 2:
        raise ValueError("base mustn't be less than 2.")
    n = abs(n)
    while n >= base:
        n, d = divmod(n, base)
        yield d
    yield n


class ErrorCode(metaclass=ABCMeta):
    """
    Error detection code abstract base class.

    Subclasses must implement at least the calculate method.
    """
    @abstractmethod
    def calculate(self, number: int) -> int:
        pass

    def is_valid(self, number: int, code: int) -> bool:
        """
        Validates a (number, code) pair by calculating the code and comparing.
        """
        return code == self.calculate(number)


class DigitSumModNCode(ErrorCode):
    """
    Digit sum mod-n error detection code.
    Does not catch digit transposition errors.
    """

    def __init__(self, mod: int):
        self.mod = mod

    @t.override
    def calculate(self, number: int) -> int:
        return sum(digits(number)) % self.mod


Type1Code = DigitSumModNCode(10)


class Mod97Code(ErrorCode):
    """
    Expand a number on the right so that its mod-97 is 1.
    This is a more advanced error detection code based on the IBAN check digits
    scheme.
    """

    @t.override
    def calculate(self, number: int) -> int:
        return 98 - (number * 100) % 97

    @t.override
    def is_valid(self, number: int, code: int) -> bool:
        return (number * 100 + code) % 97 == 1


Type2Code = Mod97Code()
