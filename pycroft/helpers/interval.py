# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import collections
from itertools import imap, izip, tee, chain, ifilterfalse
import operator


__all__ = (
    'Interval', 'closed', 'closedopen', 'openclosed', 'open', 'single', 'empty'
    'UnboundedInterval', 'IntervalSet'
)


def _infinity(name):
    """
    Create a single instance of an class with a given name.
    """
    return type(name + "Type", (object, ), {
        '__repr__': lambda self: "{0}.{1}".format(self.__module__, name),
        '__str__': lambda self: name,
        '__unicode__': lambda self: unicode(name),
    })()


PositiveInfinity = _infinity("PositiveInfinity")
NegativeInfinity = _infinity("NegativeInfinity")


class Bound(tuple):
    @property
    def value(self):
        return self[0]

    @property
    def closed(self):
        return self[1]

    def __new__(cls, value, closed):
        if value is NegativeInfinity or value is PositiveInfinity:
            closed = False
        return tuple.__new__(cls, (value, closed))

    def __init__(self, value, closed):
        """
        See __new__
        """
        super(Bound, self).__init__((value, closed))

    def __le__(self, other):
        if self.value is PositiveInfinity:
            return other.value is PositiveInfinity
        if self.value is NegativeInfinity:
            return True
        if other.value is PositiveInfinity:
            return True
        if other.value is NegativeInfinity:
            return False
        if self.value == other.value:
            return self.closed and other.closed
        return self.value <= other.value

    def __lt__(self, other):
        if self.value is PositiveInfinity:
            return other.value is PositiveInfinity
        if self.value is NegativeInfinity:
            return True
        if other.value is PositiveInfinity:
            return True
        if other.value is NegativeInfinity:
            return False
        return self.value < other.value

    def __gt__(self, other):
        return other < self

    def __ge__(self, other):
        return other <= self

    def __eq__(self, other):
        return isinstance(other, Bound) and self.value == other.value and self.closed == other.closed

    def __sub__(self, other):
        return self.value - other.value

    def __repr__(self):
        return "{0}.{1}({2!r}, {3!r})".format(
            self.__module__, self.__class__.__name__, self.value, self.closed)

    def __str__(self):
        return str(self.value)

    def __unicode__(self):
        return unicode(self.value)

    def __invert__(self):
        return Bound(self.value, not self.closed)

    @property
    def unbounded(self):
        return self.value is NegativeInfinity or self.value is PositiveInfinity


class Interval(tuple):
    """
    Represents an bound or unbound interval.

    Bounds may be any comparable types. If lengths should be calculated, bounds
    must also implement subtraction and addition.

    If a bound is None it means unbound, so a None begin is conceptually
    negative infinity and a None end positive infinity.

    This class is immutable.

    Intervals are ordered lexicographically according to begin and end per
    default.

    It implements the relations from Allen's interval algebra, i.e. before,
    during, overlaps, starts, finishes and equals.
    """
    __slots__ = ()

    def __new__(cls, begin, end):
        """
        Create a new Interval instance.

        Do not create Interval objects directly, use the utility functions
        closed, closedopen, openclosed, open, single and empty instead.
        :param Bound begin: left interval bound
        :param Bound end: right interval bound
        :raises ValueError: if begin greater than end
        """
        if begin > end:
            raise ValueError("begin > end ({0} > {1})".format(begin, end))
        # Unfortunately using namedtuple is not possible, because we have
        # field names starting with underscores
        return tuple.__new__(cls, (begin, end))

    def __init__(self, begin, end):
        """
        See __new__
        """
        super(Interval, self).__init__((begin, end))

    @property
    def _begin(self):
        return self[0]

    @property
    def _end(self):
        return self[1]

    @property
    def begin(self):
        if self._begin.value is NegativeInfinity:
            return None
        return self._begin.value

    @property
    def end(self):
        if self._end.value is PositiveInfinity:
            return None
        return self._end.value

    @property
    def unbounded(self):
        return self._begin.unbounded or self._end.unbounded

    @property
    def empty(self):
        """
        Tests if the interval is empty
        :return:
        """
        return (self._begin.value == self._end.value and
                not (self._begin.closed and self._end.closed))

    @property
    def length(self):
        """
        Compute the interval's length
        :returns: None if the interval is unbound else end - begin
        """
        return None if self.unbounded else self._end - self._begin

    def __eq__(self, other):
        return (isinstance(other, Interval) and
                self._begin == other._begin and
                self._end == other._end)

    def __le__(self, other):
        return (self._begin < other._begin or
                (self._begin == other._begin and self._end <= other._end))

    def __lt__(self, other):
        return (self._begin < other._begin or
                (self._begin == other._begin and self._end < other._end))

    def __contains__(self, point):
        bound = Bound(point, True)
        return self._begin <= bound <= self._end

    def __str__(self):
        return "{0}{1}, {2}{3}".format(
            '[' if self._begin.closed else '(',
            self._begin.value, self._end.value,
            ']' if self._end.closed else ')',
        )

    def __unicode__(self):
        return u"{0}{1}, {2}{3}".format(
            u'[' if self._begin.closed else u'(',
            self._begin.value, self._end.value,
            u']' if self._end.closed else u')',
        )

    def __repr__(self):
        if self._begin.closed:
            if self._end.closed:
                creator = "closed"
            else:
                creator = "closedopen"
        else:
            if self._end.closed:
                creator = "openclosed"
            else:
                creator = "open"
        return "{0}.{1}.{2}({3!r}, {4!r})".format(
            self.__module__,
            self.__class__.__name__,
            creator,
            self._begin.value,
            self._end.value
        )

    def strictly_before(self, other):
        """
        Tests if this interval is strictly before another interval.

        An interval is strictly before another if its end is less than the
        other's begin.

        Note: This is not the same as self < other.
        :param Interval other: another interval
        :returns: True if this interval is strictly before the other else False
        :rtype: bool
        """
        return self._end < other._begin

    def before(self, other):
        """
        Tests if this interval is before another interval.

        An interval is before another if its end is less than or equal to the
        other's begin.

        Note: This is not the same as self <= other.
        :param Interval other: another interval
        :returns: True if this interval is before the other else False
        :rtype: bool
        """
        return self._end <= other._begin

    def strictly_after(self, other):
        """
        Tests if this interval is strictly after another interval.

        An interval is strictly after another if its begin is greater than the
        other's end.

        Note: This is not the same as self > other.
        :param Interval other: another interval
        :returns: True if this interval is strictly after the other else False
        :rtype: bool
        """
        return other.strictly_before(self)

    def after(self, other):
        """
        Tests if this interval is after another interval.

        An interval is after another if its begin is greater than or equal to
        the other's end.

        Note: This is not the same as self >= other.
        :param Interval other: another interval
        :returns: True if this interval is after the other else False
        :rtype: bool
        """
        return other.before(self)

    def meets(self, other):
        """
        Tests if this interval meets another interval.

        Two intervals meet if the end of the first interval is equal to the
        begin of the second interval and at least one of the bounds is closed.
        This means that the intervals do not necessarily have to overlap.
        :param Interval other: another interval
        :returns: True if this intervals meets the other else False
        :rtype: bool
        """
        return (self._end.value == other._begin.value and
                (self._end.closed or self._begin.closed))

    def strictly_overlaps(self, other):
        """
        Tests if this interval overlaps strictly with another interval.

        Two intervals overlap if each begin is strictly before the other's end.
        This means that the intervals may not be equal.
        :param Interval other: an interval
        :returns: True if this interval overlaps strictly with the other else
        False
        :rtype: bool
        """
        return self._begin < other._end and other._begin < self._end

    def overlaps(self, other):
        """
        Tests if this interval overlaps with another interval.

        Two intervals overlap if each begin is before the other's end.
        :param Interval other: an interval
        :returns: True if this interval overlaps with the other else False
        :rtype: bool
        """
        return self._begin <= other._end and other._begin <= self._end

    def strictly_during(self, other):
        """
        Tests if this interval is strictly during (strictly contained in)
        another interval.

        An interval is strictly during another if its begin is greater than
        the other's and its end is less than the other's.
        :param Interval other: an interval
        :returns: True if this interval is strictly during the other else False
        :rtype: bool
        """
        return other._begin < self._begin and self._end < other._end

    def during(self, other):
        """
        Tests if this interval is during (contained in) another interval.

        An interval is during another if its begin is greather than or equal to
        the other's and its end is less than or equal to the other's.
        :param Interval other: an interval
        :returns: True if this interval is during the other else False
        :rtype: bool
        """
        return other._begin <= self._begin and self._end <= other._end

    def strictly_contains(self, other):
        """
        Tests if this interval strictly contains another interval.

        An interval strictly contains another if its begin is less than the
        other's and its end is greater than the other's.
        :param Interval other: an interval
        :returns: True if this interval contains the other else False
        :rtype: bool
        """
        return other.strictly_during(self)

    def contains(self, other):
        """
        Tests if this interval contains another interval.

        An interval contains another if its begin is less than or equal to the
        other's and its end greater than or equal to the other's.
        :param Interval other: an interval
        :returns: True if this interval strictly contains the other else False
        :rtype: bool
        """
        return other.during(self)

    def starts(self, other):
        """
        :param Interval other: an interval
        :rtype: bool
        """
        return self._begin == other._begin

    def finishes(self, other):
        """
        :param Interval other: an interval
        :rtype: bool
        """
        return self._end == other._end

    def intersect(self, other):
        """
        Intersect this interval with another one.

        :param Interval other: an interval
        :rtype: Interval|None
        :returns: None if the intervals do not overlap else the intersection
        """
        if not self.overlaps(other):
            return None
        return Interval(
            max(self._begin, other._begin),
            min(self._end, other._end),
        )

    __and__ = intersect
    __mul__ = intersect

    def join(self, other):
        """
        Join this interval with an interval that overlaps or meets this one.
        :param Interval other:
        :rtype: Interval|None
        :returns: None if the intervals do not overlap or meet else the union
        """
        if not self.overlaps(other) and not self.meets(other):
            return None
        return Interval(
            min(self._begin, other._begin),
            max(self._end, other._end)
        )

    __or__ = join
    __add__ = join


def _convert_begin(begin):
    return NegativeInfinity if begin is None else begin


def _convert_end(end):
    return PositiveInfinity if end is None else end


def closed(begin, end):
    """
    Create a closed interval.

    :param begin: begin
    :param end: end
    :return: closed interval [begin, end]
    :rtype: Interval
    """
    begin = _convert_begin(begin)
    end = _convert_end(end)
    return Interval(Bound(begin, True), Bound(end, True))


def closedopen(begin, end):
    """
    Create a left-closed/right-open interval.

    :param begin: begin
    :param end: end
    :return: left-closed/right-open interval [begin, end)
    :rtype: Interval
    """
    begin = _convert_begin(begin)
    end = _convert_end(end)
    return Interval(Bound(begin, True), Bound(end, False))


def openclosed(begin, end):
    """
    Create a left-open/right-closed interval.

    :param begin: begin
    :param end: end
    :return: left-open/right-closed interval (begin, end]
    :rtype: Interval
    """
    begin = _convert_begin(begin)
    end = _convert_end(end)
    return Interval(Bound(begin, False), Bound(end, True))


def open(begin, end):
    """
    Create an open interval.

    :param begin: begin
    :param end: end
    :return: open interval (begin, end)
    :rtype: Interval
    """
    begin = _convert_begin(begin)
    end = _convert_end(end)
    return Interval(Bound(begin, False), Bound(end, False))


def single(point):
    """
    Create an interval containing only a single point.
    """
    bound = Bound(point, True)
    return Interval(bound, bound)


def empty(point):
    """
    Create an empty interval positioned at the given point.

    It may seem a bit confusing that an empty interval has a location, but it
    eases the implementation of an interval a lot, as the empty interval
    does not need to be handled specially.
    """
    bound = Bound(point, False)
    return Interval(bound, bound)


UnboundedInterval = open(None, None)


class IntervalSet(collections.Sequence):
    def __init__(self, intervals):
        self._intervals = _mangle_argument(intervals)

    def __len__(self):
        return len(self._intervals)

    def length(self):
        """
        Compute the total length of the interval set, i.e. the sum of all
        interval lengths.

        The length is None if the set contains an unbounded interval.

        Note: This is not the same as len(self), which is the number of
        non-overlapping intervals.
        """
        return reduce(
            lambda a, b: None if a is None or b is None else a + b,
            imap(operator.attrgetter("length"), self._intervals)
        )

    def __iter__(self):
        return iter(self._intervals)

    def __getitem__(self, item):
        return self._intervals[item]

    def __eq__(self, other):
        return (isinstance(other, IntervalSet) and
                self._intervals == other._intervals)

    def __repr__(self):
        return "{0}.{1}({2!r})".format(
            self.__module__,
            self.__class__.__name__,
            self._intervals)

    def __str__(self):
        return "{{{0}}}".format(", ".join(imap(str, self._intervals)))

    def __unicode__(self):
        return u"{{{0}}}".format(u", ".join(imap(unicode, self._intervals)))

    def complement(self):
        return _create(_complement(self._intervals))

    __invert__ = complement
    __neg__ = complement

    def union(self, other):
        """
        :param IntervalSet other:
        :return:
        """
        other_intervals = _mangle_argument(other)
        return _create(_join(_chain_ordered(self._intervals, other_intervals)))

    __or__ = union
    __add__ = union

    def intersect(self, other):
        other_intervals = _mangle_argument(other)
        return _create(_intersect(self._intervals, other_intervals))

    __and__ = intersect
    __mul__ = intersect

    def difference(self, other):
        other_intervals = _mangle_argument(other)
        return self.intersect(_complement(other_intervals))

    __sub__ = difference


def _mangle_argument(arg):
    if isinstance(arg, IntervalSet):
        return arg._intervals
    if isinstance(arg, Interval):
        return (arg,)
    if isinstance(arg, collections.Iterable):
        return tuple(_join(sorted(arg)))
    raise TypeError("Argument may be an IntervalSet, an Interval or an iterable"
                    "of Intervals. Was {0}.".format(type(arg).__name__))


def _create(intervals):
    """
    Create an IntervalSet directly from a sorted Interval iterable.
    :param iterable[Interval] intervals:
    :rtype: IntervalSet
    :return:
    """
    interval_set = IntervalSet(())
    interval_set._intervals = tuple(intervals)
    return interval_set


def _chain_ordered(left, right):
    """
    :param iterable[Interval] left:
    :param iterable[Interval] right:
    :rtype: iterable[Interval]
    :return:
    """
    left = iter(left)
    right = iter(right)
    a = next(left, None)
    b = next(right, None)
    while a is not None and b is not None:
        if a < b:
            yield a
            a = next(left, None)
        else:
            yield b
            b = next(right, None)
    if a is not None:
        yield a
        for a in left:
            yield a
    if b is not None:
        yield b
        for b in right:
            yield b


def _complement(intervals):
    """

    :param iterable[Interval] intervals:
    :return:
    :rtype: iterable[Interval]
    """
    intervals = iter(intervals)
    try:
        first = next(intervals)
    except StopIteration:
        yield UnboundedInterval
        raise StopIteration()
    if not first._begin.unbounded:
        yield Interval(Bound(NegativeInfinity, False), ~first._begin)
    a, b = tee(intervals)
    last = first
    for current_interval, next_interval in izip(chain((first,), a), b):
        yield Interval(~current_interval._end, ~next_interval._begin)
        last = next_interval
    if not last._end.unbounded:
        yield Interval(~last._end, Bound(PositiveInfinity, False))


def _join(intervals):
    """
    Join a possibly overlapping, ordered iterable of intervals, removing any
    empty intervals.

    The intervals must be sorted according to begin primarily and
    end secondarily.
    :param iterable[Interval] intervals: sorted iterable of intervals
    :returns: merged list of intervals
    :rtype: iterable[Interval]
    """
    intervals = ifilterfalse(operator.attrgetter("empty"), iter(intervals))
    top = next(intervals)
    for interval in intervals:
        join = top.join(interval)
        if join is None or join.empty:
            yield top
            top = interval
        else:
            top = join
    yield top


def _intersect(left, right):
    """

    :param iterable[Interval] left:
    :param iterable[Interval] right:
    :rtype: iterable[Interval]
    :return:
    """
    left = iter(left)
    right = iter(right)
    a = next(left)
    b = next(right)
    while True:
        intersect = a.intersect(b)
        if intersect is not None and not intersect.empty:
            yield intersect
        if cmp(a._end, b._end) < 0:
            a = next(left)
        else:
            b = next(right)
