# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import collections
from itertools import tee, chain, filterfalse
import operator
from functools import reduce

from sqlalchemy import Column, func, CheckConstraint, or_, literal, and_, null
from sqlalchemy.ext.hybrid import hybrid_method
from sqlalchemy.orm import validates, object_session

from pycroft.model import session
from pycroft.model.base import IntegerIdModel
from pycroft.model.types import DateTimeTz

__all__ = (
    'Interval', 'closed', 'closedopen', 'openclosed', 'open', 'single', 'empty',
    'UnboundedInterval', 'IntervalSet'
)


def _infinity(name):
    """
    Create a single instance of an class with a given name.
    """
    return type(name + "Type", (object, ), {
        '__repr__': lambda self: "{0}.{1}".format(self.__module__, name),
        '__str__': lambda self: name,
        '__unicode__': lambda self: name,
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

    def __new__(cls, value, is_closed):
        if value is NegativeInfinity or value is PositiveInfinity:
            is_closed = False
        return tuple.__new__(cls, (value, is_closed))

    def __hash__(self):
        return hash((self[0], self[1]))

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
        return (isinstance(other, Bound) and
                self.value == other.value and
                self.closed == other.closed)

    def __sub__(self, other):
        return self.value - other.value

    def __repr__(self):
        return "{0}.{1}({2!r}, {3!r})".format(
            self.__module__, self.__class__.__name__, self.value, self.closed)

    def __str__(self):
        return str(self.value)

    def __unicode__(self):
        return str(self.value)

    def __invert__(self):
        return Bound(self.value, not self.closed)

    @property
    def unbounded(self):
        return self.value is NegativeInfinity or self.value is PositiveInfinity


class Interval(tuple):
    """
    Represents an bounded or unbounded interval.

    Bounds may be any comparable types. If lengths should be calculated, bounds
    must also implement subtraction and the return type of the subtraction must
    implement addition.

    If a bound is None it means unbound, so a None begin is conceptually
    negative infinity and a None end positive infinity.

    This class is immutable.

    Intervals are ordered lexicographically according to begin and end per
    default.

    It implements the relations from Allen's interval algebra, i.e. before,
    during, overlaps, starts, finishes and equals.
    """
    __slots__ = ()

    def __new__(cls, lower_bound, upper_bound):
        """
        Create a new Interval instance.

        Usually, the utility functions closed, closedopen, openclosed, open,
        single and empty should be used instead of creating Interval objects
        directly.
        :param Bound lower_bound: left interval bound
        :param Bound upper_bound: right interval bound
        :raises ValueError: if lower_bound greater than upper_bound
        """
        if lower_bound > upper_bound:
            raise ValueError(
                "lower_bound > upper_bound ({0} > {1})"
                .format(lower_bound, upper_bound)
            )
        # Unfortunately using namedtuple is not possible, because we have
        # field names starting with underscores
        return tuple.__new__(cls, (lower_bound, upper_bound))

    def __hash__(self):
        return hash((self[0], self[1]))

    @property
    def lower_bound(self):
        """
        :rtype: Bound
        :returns: The lower bound object
        """
        return self[0]

    @property
    def upper_bound(self):
        """
        :rtype: Bound
        :returns: The upper bound object
        """
        return self[1]

    @property
    def begin(self):
        if self.lower_bound.value is NegativeInfinity:
            return None
        return self.lower_bound.value

    @property
    def end(self):
        if self.upper_bound.value is PositiveInfinity:
            return None
        return self.upper_bound.value

    @property
    def unbounded(self):
        return self.lower_bound.unbounded or self.upper_bound.unbounded

    @property
    def empty(self):
        """
        Tests if the interval is empty
        :return:
        """
        return (self.lower_bound.value == self.upper_bound.value and
                not (self.lower_bound.closed and self.upper_bound.closed))

    @property
    def length(self):
        """
        Compute the interval's length
        :returns: None if the interval is unbound else end - begin
        """
        return None if self.unbounded else self.upper_bound - self.lower_bound

    def __eq__(self, other):
        return (isinstance(other, Interval) and
                self.lower_bound == other.lower_bound and
                self.upper_bound == other.upper_bound)

    def __le__(self, other):
        return (self.lower_bound < other.lower_bound or
                (self.lower_bound == other.lower_bound and
                 self.upper_bound <= other.upper_bound))

    def __lt__(self, other):
        return (self.lower_bound < other.lower_bound or
                (self.lower_bound == other.lower_bound and
                 self.upper_bound < other.upper_bound))

    def __contains__(self, point):
        bound = Bound(point, True)
        return self.lower_bound <= bound <= self.upper_bound

    def __str__(self):
        return "{0}{1}, {2}{3}".format(
            '[' if self.lower_bound.closed else '(',
            self.lower_bound.value, self.upper_bound.value,
            ']' if self.upper_bound.closed else ')',
        )

    def __unicode__(self):
        return u"{0}{1}, {2}{3}".format(
            u'[' if self.lower_bound.closed else u'(',
            self.lower_bound.value, self.upper_bound.value,
            u']' if self.upper_bound.closed else u')',
        )

    def __repr__(self):
        if self.lower_bound.closed:
            if self.upper_bound.closed:
                creator = "closed"
            else:
                creator = "closedopen"
        else:
            if self.upper_bound.closed:
                creator = "openclosed"
            else:
                creator = "open"
        return "{0}.{1}.{2}({3!r}, {4!r})".format(
            self.__module__,
            self.__class__.__name__,
            creator,
            self.lower_bound.value,
            self.upper_bound.value
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
        return self.upper_bound < other.lower_bound

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
        return self.upper_bound <= other.lower_bound

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
        return (self.upper_bound.value == other.lower_bound.value and
                (self.upper_bound.closed or self.lower_bound.closed))

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
        return (self.lower_bound < other.upper_bound and
                other.lower_bound < self.upper_bound)

    def overlaps(self, other):
        """
        Tests if this interval overlaps with another interval.

        Two intervals overlap if each begin is before the other's end.
        :param Interval other: an interval
        :returns: True if this interval overlaps with the other else False
        :rtype: bool
        """
        return (self.lower_bound <= other.upper_bound and
                other.lower_bound <= self.upper_bound)

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
        return (other.lower_bound < self.lower_bound and
                self.upper_bound < other.upper_bound)

    def during(self, other):
        """
        Tests if this interval is during (contained in) another interval.

        An interval is during another if its begin is greather than or equal to
        the other's and its end is less than or equal to the other's.
        :param Interval other: an interval
        :returns: True if this interval is during the other else False
        :rtype: bool
        """
        return (other.lower_bound <= self.lower_bound and
                self.upper_bound <= other.upper_bound)

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
        return self.lower_bound == other.lower_bound

    def finishes(self, other):
        """
        :param Interval other: an interval
        :rtype: bool
        """
        return self.upper_bound == other.upper_bound

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
            max(self.lower_bound, other.lower_bound),
            min(self.upper_bound, other.upper_bound),
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
            min(self.lower_bound, other.lower_bound),
            max(self.upper_bound, other.upper_bound)
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
    def __init__(self, intervals=None):
        self._intervals = _mangle_argument(intervals)

    def __hash__(self):
        return hash(self._intervals)

    def __bool__(self):
        return True if self._intervals else False

    def __len__(self):
        return len(self._intervals)

    @property
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
            (i.length for i in self._intervals)
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
        return "{{{0}}}".format(", ".join(str(i) for i in self._intervals))

    def __unicode__(self):
        return u"{{{0}}}".format(u", ".join(str(i) for i in self._intervals))

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
    if arg is None:
        return ()
    if isinstance(arg, IntervalSet):
        return arg._intervals
    if isinstance(arg, Interval):
        return (arg,)
    if isinstance(arg, collections.Iterable):
        return tuple(_join(sorted(arg)))
    raise TypeError("Argument may be None, an IntervalSet, an Interval or an "
                    "iterable of Intervals. "
                    "Was {0}.".format(type(arg).__name__))


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
        return
    if not first.lower_bound.unbounded:
        yield Interval(Bound(NegativeInfinity, False), ~first.lower_bound)
    a, b = tee(intervals)
    last = first
    for current_, next_ in zip(chain((first,), a), b):
        yield Interval(~current_.upper_bound, ~next_.lower_bound)
        last = next_
    if not last.upper_bound.unbounded:
        yield Interval(~last.upper_bound, Bound(PositiveInfinity, False))


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
    intervals = filterfalse(operator.attrgetter("empty"), iter(intervals))
    try:
        top = next(intervals)
    except StopIteration:
        return
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
    try:
        a = next(left)
        b = next(right)
        while True:
            intersect = a.intersect(b)
            if intersect is not None and not intersect.empty:
                yield intersect
            if a.upper_bound < b.upper_bound:
                a = next(left)
            else:
                b = next(right)
    except StopIteration:
        return


class IntervalModel:
    begins_at = Column(DateTimeTz, nullable=True, index=True, server_default=func.current_timestamp())
    ends_at = Column(DateTimeTz, nullable=True, index=True)

    __table_args = (
        CheckConstraint("begins_at IS NULL OR "
                        "ends_at IS NULL OR "
                        "begins_at <= moved_out")
    )

    @hybrid_method
    def active(self, when=None):
        """
        Tests if overlaps with a given interval. If no interval is
        given, it tests if active right now.
        :param Interval when: interval to test
        :rtype: bool
        """
        if when is None:
            now = object_session(self).query(func.current_timestamp()).scalar()
            when = single(now)

        return when.overlaps(closed(self.begins_at, self.ends_at))

    @active.expression
    def active(cls, when=None):
        """
        Tests if overlaps with a given interval. If no interval is
        given, it tests if active right now.
        :param Interval when:
        :return:
        """
        if when is None:
            now = session.utcnow()
            when = single(now)

        return and_(
            or_(cls.begins_at == null(), literal(when.end) == null(),
                cls.begins_at <= literal(when.end)),
            or_(literal(when.begin) == null(), cls.ends_at == null(),
                literal(when.begin) <= cls.ends_at)
        ).label("active")

    @validates('ends_at')
    def validate_ends_at(self, _, value):
        if value is None:
            return value
        if self.begins_at is not None:
            assert value >= self.begins_at,\
                "begins_at must be before ends_at"
        return value

    @validates('begins_at')
    def validate_begins_at(self, _, value):
        if value is None:
            return value
        if self.ends_at is not None:
            assert value <= self.ends_at,\
                "begins_at must be before ends_at"
        return value

    def disable(self, ends_at=None):
        if ends_at is None:
            ends_at = object_session(self).query(func.current_timestamp()).scalar()

        if self.begins_at is not None and self.begins_at > ends_at:
            self.ends_at = self.begins_at
        else:
            self.ends_at = ends_at
