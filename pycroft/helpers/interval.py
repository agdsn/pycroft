# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import collections


class Interval(collections.namedtuple('BaseInterval', ['begin', 'end'])):
    """
    Represents an bound or unbound interval.

    Bounds may be any comparable types. If lengths should be calculated, bounds
    must also implement subtraction. If a bound is None it means unbound, so
    a None begin is conceptually negative infinity and a None end positive
    infinity. This class is immutable.
    It implements the relations from Allen's interval algebra, i.e. before,
    during, overlaps, starts, finishes and equals.
    """

    @staticmethod
    def _lt(a, b):
        return a is None or b is None or a < b

    @staticmethod
    def _gt(a, b):
        return a is None or b is None or a > b

    @staticmethod
    def _le(a, b):
        return a is None or b is None or a <= b

    @staticmethod
    def _ge(a, b):
        return a is None or b is None or a >= b

    @staticmethod
    def _eq(a, b):
        return not (a is None and b is None) and (a == b)

    @staticmethod
    def _max(a, b):
        if a is None:
            return b
        if b is None:
            return a
        return max(a, b)

    @staticmethod
    def _min(a, b):
        if a is None:
            return b
        if b is None:
            return a
        return min(a, b)

    def __init__(self, begin, end):
        """
        :param begin: right interval boundary
        :param end: left interval boundary
        :raises ValueError: if begin greater than end
        """
        if begin is not None and end is not None and begin > end:
            raise ValueError(
                "begin {0} is greater than end {1}.".format(begin, end)
            )
        super(Interval, self).__init__((begin, end))

    def __eq__(self, other):
        return self.begin == other.begin and self.end == other.end

    def __lt__(self, other):
        """
        :param Interval other: an interval
        :rtype: bool
        """
        return (self.end is not None and
                other.begin is not None and
                self.end < other.begin)

    def __le__(self, other):
        """
        :param Interval other: an interval
        :rtype: bool
        """
        return (self.end is not None and
                other.begin is not None and
                self.end <= other.begin)

    def __gt__(self, other):
        """
        :param Interval other: an interval
        :rtype: bool
        """
        return other.__lt__(self)

    def __ge__(self, other):
        """
        :param Interval other: an interval
        :rtype: bool
        """
        return other.__le__(self)

    def __str__(self):
        return "[{0}, {1}]".format(self.begin, self.end)

    def __unicode__(self):
        return unicode(self.__str__)

    def __repr__(self):
        return self.__str__()

    def strictly_before(self, other):
        """Alias for i1 < i2."""
        return self.__lt__(other)

    def before(self, other):
        """Alias for i1 <= i2."""
        return self.__le__(other)

    def strictly_after(self, other):
        """Alias for i1 > i2."""
        return self.__gt__(other)

    def after(self, other):
        """Alias for i1 >= i2."""
        return self.__ge__(other)

    def is_unbound(self):
        return self.begin is None or self.end is None

    def meets(self, other):
        return self._eq(self.end, other.begin)

    def overlaps_strictly(self, other):
        """
        :param Interval other: an interval
        :rtype: bool
        """
        return (self._lt(self.begin, other.end) and
                self._lt(other.begin, self.end))

    def overlaps(self, other):
        """
        :param Interval other: an interval
        :rtype: bool
        """
        return (self._le(self.begin, other.end) and
                self._le(other.begin, self.end))

    def strictly_during(self, other):
        """
        :param Interval other: an interval
        :rtype: bool
        """
        return (self._lt(other.begin, self.begin) and
                self._lt(self.end, other.end))

    def during(self, other):
        """
        :param Interval other: an interval
        :rtype: bool
        """
        return (self._le(other.begin, self.begin) and
                self._le(self.end, other.end))

    def contains(self, other):
        """
        :param Interval other: an interval
        :rtype: bool
        """
        return other.during(self)

    def strictly_contains(self, other):
        """
        :param Interval other: an interval
        :rtype: bool
        """
        return other.strictly_during(self)

    def starts(self, other):
        """
        :param Interval other: an interval
        :rtype: bool
        """
        return self.begin == other.begin

    def finishes(self, other):
        """
        :param Interval other: an interval
        :rtype: bool
        """
        return self.end == other.end

    def length(self):
        """
        Compute the interval's length
        :returns: None if the interval is unbound else end - begin
        """
        return None if self.is_unbound() else self.end - self.begin

    def intersect(self, other):
        """
        Intersect interval with another one.

        :param Interval other: an interval
        :rtype: Interval|None
        :returns: None if the intervals do not overlap else an Interval
        representing the intersection.
        """
        if not self.overlaps(other):
            return None
        return Interval(
            self._max(self.begin, other.begin),
            self._min(self.end, other.end)
        )
