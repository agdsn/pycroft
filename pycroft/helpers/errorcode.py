from abc import ABCMeta, abstractmethod


def digits(n, base=10):
    """
    Generate all digits of number in a given base starting with the least
    significant digit.
    :param Integral n: An integral number
    :param Integral base: Defaults to 10.
    """
    if base < 2:
        raise ValueError("base mustn't be less than 2.")
    n = abs(n)
    while n >= base:
        n, d = divmod(n, base)
        yield d
    yield n


class ErrorCode(object):
    """
    Error detection code abstract base class.

    Subclasses must implement at least the calculate method.
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def calculate(self, number):
        pass

    def is_valid(self, number, code):
        """
        Validates a (number, code) pair by calculating the code and comparing.
        """
        return code == self.calculate(number)


class DigitSumModNCode(ErrorCode):
    """
    Digit sum mod-n error detection code.
    Does not catch digit transposition errors.
    """
    def __init__(self, mod):
        self.mod = mod

    def calculate(self, number):
        return sum(digits(number)) % self.mod


Type1Code = DigitSumModNCode(10)


class Mod97Code(ErrorCode):
    """
    Expand a number on the right so that its mod-97 is 1.
    This is a more advanced error detection code based on the IBAN check digits
    scheme.
    """
    def calculate(self, number):
        return 98 - (number * 100) % 97

    def is_valid(self, number, code):
        return (number * 100 + code) % 97 == 1


Type2Code = Mod97Code()
