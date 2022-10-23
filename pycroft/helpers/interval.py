# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
pycroft.helpers.interval
~~~~~~~~~~~~~~~~~~~~~~~~
"""
from __future__ import annotations

import collections.abc
import operator
import typing as t
from functools import reduce
from itertools import tee, chain, filterfalse
from typing import Generic

if t.TYPE_CHECKING:
    from _typeshed import SupportsAllComparisons
    # TODO figure out how we can demand that T shall be a totally ordered metric space
    T = t.TypeVar("T", bound=SupportsAllComparisons)
    U = t.TypeVar("U", bound=SupportsAllComparisons)
else:
    T = t.TypeVar("T")
    U = t.TypeVar("U")


def _infinity(name):
    """
    Create a single instance of an class with a given name.
    """
    return type(name + "Type", (object, ), {
        '__repr__': lambda self: f"{self.__module__}.{name}",
        '__str__': lambda self: name,
        '__unicode__': lambda self: name,
    })()


#: +∞
PositiveInfinity = _infinity("PositiveInfinity")


class PositiveInfinityType:
    """dummy placeholder type to work around mypy limitations"""

    pass


#: -∞
NegativeInfinity = _infinity("NegativeInfinity")


class NegativeInfinityType:
    """dummy placeholder type to work around mypy limitations"""

    pass


TWithInfinity: t.TypeAlias = T | PositiveInfinityType | NegativeInfinityType


class Bound(tuple, Generic[T]):
    """Represents a bound of an interval, i.e. value + closedness.

    The value is either:

    * a direct value (of the underlying, totally ordeered value type ``T``)
    * :data:`PositiveInfinity`
    * :data:`NegativeInfinity`
    """

    @property
    def value(self) -> TWithInfinity:
        return self[0]

    @property
    def closed(self) -> bool:
        return t.cast(bool, self[1])

    @property
    def pg_identifier(self) -> str:
        if self.value is PositiveInfinity or self.value is NegativeInfinity:
            # in postgres tstzranges, there exists the lower bound `-infinity`,
            # but that is not quite the same as the empty lower bound (same for upper).
            # To see why we don't use `±infinity`, stare at this query
            # and open a strong alcoholic beverage.
            # pycroft=# select tsrange '(,today)' - '[-infinity, today)';
            # ?column?
            # (,-infinity)
            return ''
        return str(self.value)

    def __new__(cls, value: TWithInfinity, is_closed: bool) -> Bound[T]:
        if value is NegativeInfinity or value is PositiveInfinity:
            is_closed = False
        return tuple.__new__(cls, (value, is_closed))

    def __hash__(self) -> int:
        return hash((self[0], self[1]))

    def __le__(self, other: Bound[T]) -> bool:  # type: ignore
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
        return t.cast(T, self.value) <= t.cast(T, other.value)

    def __lt__(self, other: Bound[T]) -> bool:  # type: ignore
        if self.value is PositiveInfinity:
            return other.value is PositiveInfinity
        if self.value is NegativeInfinity:
            return True
        if other.value is PositiveInfinity:
            return True
        if other.value is NegativeInfinity:
            return False
        return t.cast(T, self.value) < t.cast(T, other.value)

    def __gt__(self, other: Bound[T]) -> bool:  # type: ignore
        return other < self

    def __ge__(self, other: Bound[T]) -> bool:  # type: ignore
        return other <= self

    def __eq__(self, other: object) -> bool:
        return (isinstance(other, Bound) and
                self.value == other.value and
                self.closed == other.closed)

    def __sub__(self, other):
        return self.value - other.value

    def __repr__(self):
        return "{}.{}({!r}, {!r})".format(
            self.__module__, self.__class__.__name__, self.value, self.closed)

    def __str__(self):
        return str(self.value)

    def __unicode__(self):
        return str(self.value)

    def __invert__(self):
        return Bound(self.value, not self.closed)

    @property
    def unbounded(self) -> bool:
        return self.value is NegativeInfinity or self.value is PositiveInfinity


class Interval(tuple, Generic[T]):
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

    .. todo:: replace by generic namedtuple once we're on
        `Python 3.11 <https://docs.python.org/3.11/whatsnew/3.11.html#typing>`_
        for nicer typing behavior
    """
    __slots__ = ()

    def __new__(cls, lower_bound: Bound[T], upper_bound: Bound[T]) -> Interval[T]:
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
                f"lower_bound > upper_bound ({lower_bound} > {upper_bound})"
            )
        # Unfortunately using namedtuple is not possible, because we have
        # field names starting with underscores
        return tuple.__new__(cls, (lower_bound, upper_bound))

    @classmethod
    def from_explicit_data(
        cls,
        lower: T | None, lower_closed: bool,
        upper: T | None, upper_closed: bool,
    ) -> Interval[T]:
        return cls(Bound(_convert_begin(lower), lower_closed),
                   Bound(_convert_end(upper), upper_closed))

    def __hash__(self):
        return hash((self[0], self[1]))

    @property
    def lower_bound(self) -> Bound[T]:
        """
        :returns: The lower bound object
        """
        return t.cast(Bound[T], self[0])

    @property
    def upper_bound(self) -> Bound[T]:
        """
        :returns: The upper bound object
        """
        return t.cast(Bound[T], self[1])

    @property
    def begin(self) -> T | None:
        if self.lower_bound.value is NegativeInfinity:
            return None
        return t.cast(T, self.lower_bound.value)

    @property
    def end(self) -> T | None:
        if self.upper_bound.value is PositiveInfinity:
            return None
        return t.cast(T, self.upper_bound.value)

    @property
    def unbounded(self) -> bool:
        return self.lower_bound.unbounded or self.upper_bound.unbounded

    @property
    def empty(self) -> bool:
        """Tests whether the interval is empty"""
        return (self.lower_bound.value == self.upper_bound.value and
                not (self.lower_bound.closed and self.upper_bound.closed))

    @property
    def length(self) -> t.Any:  # actually return type of `T.__sub__`
        """Compute the interval's length

        :returns: ``None`` if the interval is unbounded else ``end - begin``
        """
        return None if self.unbounded else self.upper_bound - self.lower_bound

    def __eq__(self, other: object) -> bool:
        return (isinstance(other, Interval) and
                self.lower_bound == other.lower_bound and
                self.upper_bound == other.upper_bound)

    def __le__(self, other: Interval[T]) -> bool:  # type: ignore
        return (self.lower_bound < other.lower_bound or
                (self.lower_bound == other.lower_bound and
                 self.upper_bound <= other.upper_bound))

    def __lt__(self, other: Interval[T]) -> bool:  # type: ignore
        return (self.lower_bound < other.lower_bound or
                (self.lower_bound == other.lower_bound and
                 self.upper_bound < other.upper_bound))

    def __contains__(self, point: T) -> bool:  # type: ignore
        bound = Bound[T](point, True)
        return self.lower_bound <= bound <= self.upper_bound

    def __str__(self):
        return "{}{},{}{}".format(
            '[' if self.lower_bound.closed else '(',
            self.lower_bound.pg_identifier, self.upper_bound.pg_identifier,
            ']' if self.upper_bound.closed else ')',
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
        return "{}.{}.{}({!r}, {!r})".format(
            self.__module__,
            self.__class__.__name__,
            creator,
            self.lower_bound.value,
            self.upper_bound.value
        )

    def strictly_before(self, other: Interval[T]) -> bool:
        """
        Tests if this interval is strictly before another interval.

        An interval is strictly before another if its end is less than the
        other's begin.

        .. note:: This is not the same as ``self < other``.
        """
        return self.upper_bound < other.lower_bound

    def before(self, other: Interval[T]) -> bool:
        """
        Tests if this interval is before another interval.

        An interval is before another if its end is less than or equal to the
        other's begin.

        .. note:: This is not the same as ``self <= other``.
        """
        return self.upper_bound <= other.lower_bound

    def strictly_after(self, other: Interval[T]) -> bool:
        """
        Tests if this interval is strictly after another interval.

        An interval is strictly after another if its begin is greater than the
        other's end.

        .. note:: This is not the same as ``self > other``.
        """
        return other.strictly_before(self)

    def after(self, other: Interval[T]) -> bool:
        """
        Tests if this interval is after another interval.

        An interval is after another if its begin is greater than or equal to
        the other's end.

        .. note:: This is not the same as ``self >= other``.
        """
        return other.before(self)

    def meets(self, other: Interval[T]) -> bool:
        """
        Tests if this interval meets another interval.

        Two intervals meet if the end of the first interval is equal to the
        begin of the second interval and at least one of the bounds is closed.
        This means that the intervals do not necessarily have to overlap.
        """
        return (self.upper_bound.value == other.lower_bound.value and
                (self.upper_bound.closed or self.lower_bound.closed))

    def strictly_overlaps(self, other: Interval[T]) -> bool:
        """
        Tests if this interval overlaps strictly with another interval.

        Two intervals overlap if each begin is strictly before the other's end.
        This means that the intervals may not be equal.
        """
        return (self.lower_bound < other.upper_bound and
                other.lower_bound < self.upper_bound)

    def overlaps(self, other: Interval[T]) -> bool:
        """
        Tests if this interval overlaps with another interval.

        Two intervals overlap if each begin is before the other's end.
        """
        return (self.lower_bound <= other.upper_bound and
                other.lower_bound <= self.upper_bound)

    def strictly_during(self, other: Interval[T]) -> bool:
        """
        Tests if this interval is strictly during (strictly contained in)
        another interval.

        An interval is strictly during another if its begin is greater than
        the other's and its end is less than the other's.
        """
        return (other.lower_bound < self.lower_bound and
                self.upper_bound < other.upper_bound)

    def during(self, other: Interval[T]) -> bool:
        """
        Tests if this interval is during (contained in) another interval.

        An interval is during another if its begin is greather than or equal to
        the other's and its end is less than or equal to the other's.
        """
        return (other.lower_bound <= self.lower_bound and
                self.upper_bound <= other.upper_bound)

    def strictly_contains(self, other: Interval[T]) -> bool:
        """
        Tests if this interval strictly contains another interval.

        An interval strictly contains another if its begin is less than the
        other's and its end is greater than the other's.
        """
        return other.strictly_during(self)

    def contains(self, other: Interval[T]) -> bool:
        """
        Tests if this interval contains another interval.

        An interval contains another if its begin is less than or equal to the
        other's and its end greater than or equal to the other's.
        """
        return other.during(self)

    def starts(self, other: Interval[T]) -> bool:
        """Tests whether both intervals start at the same value."""
        return self.lower_bound == other.lower_bound

    def finishes(self, other: Interval[T]) -> bool:
        """Tests whether both intervals finish at the same value."""
        return self.upper_bound == other.upper_bound

    def intersect(self, other: Interval[T]) -> Interval[T] | None:
        """
        Intersect this interval with another one.

        :returns: ``None`` if the intervals do not overlap else the intersection
        """
        if not self.overlaps(other):
            return None
        return Interval(
            max(self.lower_bound, other.lower_bound),
            min(self.upper_bound, other.upper_bound),
        )

    __and__ = intersect
    __mul__ = intersect  # type: ignore

    def join(self, other: Interval[T]) -> Interval[T] | None:
        """
        Join this interval with an interval that overlaps or meets this one.

        :returns: None if the intervals do not overlap or meet else the union
        """
        if not self.overlaps(other) and not self.meets(other):
            return None
        return Interval(
            min(self.lower_bound, other.lower_bound),
            max(self.upper_bound, other.upper_bound)
        )

    @property
    def closure(self) -> Interval[T]:
        """Return a closed variant of this interval"""
        return Interval(Bound(self.lower_bound.value, is_closed=True),
                        Bound(self.upper_bound.value, is_closed=True))

    __or__ = join
    __add__ = join  # type: ignore

    def __sub__(self, other: Interval[T]):
        if not (other.upper_bound.unbounded or other.lower_bound.unbounded):
            raise ValueError("You can only subtract a ray from an interval!")
        diff_set = IntervalSet[T]([self]) - other
        assert len(diff_set) == 1
        return diff_set[0]

    def map(self, f: t.Callable[[T], U]) -> Interval[U]:
        r"""Apply a monotonic function to the interval's bounds.

        For instance, the following would turn a :class:`datetime` interval into a
        :class:`date` interval by mapping ``dt↦dt.date()``:

        >>> from datetime import datetime, date
        >>> i = starting_from(datetime.fromisoformat("2020-01-01T00:00:00Z"))
        >>> i_dates = i.map(lambda dt: dt.date())
        >>> assert i_dates == starting_from(date(2020, 1, 1))

        .. note:: This turns :class:`Interval` into a functor from the category of
            linearly ordered types (i.e., ``SupportsAllComparisons``) to the category of types.
            In other words, for every map :math:`f:T→U`,
            we get a corresponding map :math:`Ff: \mathrm{Interval}[T]→\mathrm{Interval}[U]`
            in a way which

            * preserves identity, i.e. ``i.map(lambda x: x) == i``
            * satisfies :math:`F(f\circ g) = Ff \circ Fg`,
              i.e. ``i.map(f).map(g) == i.map(lambda x: g(f(x))``

        .. hint:: monotonicity is necessary because otherwise there is some pair of values
            :math:`(x, y)` such that the values :math:`(f(x), f(y))` are invalid
            as bounds for an interval.

        :param f: A monotonic function (that is, a function satisfying :math:`x≤y⇒f(x)≤f(y)`
            for all :math:`x, y: T`)
        :return: A new interval with f applied to its bounds
        """
        return Interval[U](
            t.cast(Bound[U], l) if (l := self.lower_bound).unbounded
            else Bound[U](f(t.cast(T, l.value)), l.closed),
            t.cast(Bound[U], u) if (u := self.lower_bound).unbounded
            else Bound[U](f(t.cast(T, u.value)), u.closed),
        )

def _convert_begin(begin: T | None) -> TWithInfinity:
    return t.cast(TWithInfinity, NegativeInfinity) if begin is None else begin


def _convert_end(end: T | None) -> TWithInfinity:
    return t.cast(TWithInfinity, PositiveInfinity) if end is None else end


def closed(begin: T | None, end: T | None) -> Interval[T]:
    """
    Create a closed interval.

    :return: closed interval [begin, end]
    """
    begin_ = _convert_begin(begin)
    end_ = _convert_end(end)
    return Interval(Bound(begin_, True), Bound(end_, True))


def closedopen(begin: T | None, end: T | None) -> Interval[T]:
    """
    Create a left-closed/right-open interval.

    :return: left-closed/right-open interval [begin, end)
    """
    begin_ = _convert_begin(begin)
    end_ = _convert_end(end)
    return Interval(Bound(begin_, True), Bound(end_, False))


def starting_from(when: T) -> Interval[T]:
    """Alias for :func:`closedopen(when, None) <closedopen>`

    :return: ``[when, ∞)``
    """
    return closedopen(when, None)


def openclosed(begin: T | None, end: T | None) -> Interval[T]:
    """
    Create a left-open/right-closed interval.

    :return: left-open/right-closed interval (begin, end]
    """
    begin_ = _convert_begin(begin)
    end_ = _convert_end(end)
    return Interval(Bound(begin_, False), Bound(end_, True))


def open(begin: T | None, end: T | None) -> Interval[T]:
    """
    Create an open interval.

    :return: open interval (begin, end)
    """
    begin_ = _convert_begin(begin)
    end_ = _convert_end(end)
    return Interval(Bound(begin_, False), Bound(end_, False))


def single(point: T) -> Interval[T]:
    """
    Create an interval containing only a single point.
    """
    bound = Bound[T](point, True)
    return Interval(bound, bound)


def empty(point: T) -> Interval[T]:
    """
    Create an empty interval positioned at the given point.

    It may seem a bit confusing that an empty interval has a location, but it
    eases the implementation of an interval a lot, as the empty interval
    does not need to be handled specially.
    """
    bound = Bound[T](point, False)
    return Interval(bound, bound)


#:
UnboundedInterval = open(None, None)


class IntervalSet(collections.abc.Sequence[Interval[T]], Generic[T]):
    _intervals: tuple[Interval[T], ...]

    def __init__(
        self,
        intervals: IntervalSetSource = None,
    ):
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

    def __iter__(self) -> t.Iterator[Interval[T]]:
        return iter(self._intervals)

    def __getitem__(self, item):
        return self._intervals[item]

    def __eq__(self, other):
        return (isinstance(other, IntervalSet) and
                self._intervals == other._intervals)

    def __repr__(self):
        return "{}.{}({!r})".format(
            self.__module__,
            self.__class__.__name__,
            self._intervals)

    def __str__(self):
        return "{{{0}}}".format(", ".join(str(i) for i in self._intervals))

    def __unicode__(self):
        return "{{{0}}}".format(", ".join(str(i) for i in self._intervals))

    def complement(self):
        return _create(_complement(self._intervals))

    __invert__ = complement
    __neg__ = complement

    def union(self, other: IntervalSetSource) -> IntervalSet[T]:
        other_intervals: tuple[Interval[T], ...] = _mangle_argument(other)
        return _create(_join(_chain_ordered(self._intervals, other_intervals)))

    __or__ = union
    __add__ = union

    def intersect(self, other: IntervalSetSource) -> IntervalSet[T]:
        other_intervals: tuple[Interval[T], ...] = _mangle_argument(other)
        return _create(_intersect(self._intervals, other_intervals))

    __and__ = intersect
    __mul__ = intersect

    def difference(self, other: IntervalSetSource) -> IntervalSet[T]:
        other_intervals: tuple[Interval[T], ...] = _mangle_argument(other)
        return self.intersect(_complement(other_intervals))

    __sub__ = difference


#:
IntervalSetSource = Interval[T] | IntervalSet[T] | t.Iterable[Interval[T]] | None


def _mangle_argument(arg: IntervalSetSource) -> tuple[Interval[T], ...]:
    if arg is None:
        return ()
    if isinstance(arg, IntervalSet):
        return arg._intervals
    if isinstance(arg, Interval):
        return (arg,)
    if isinstance(arg, collections.abc.Iterable):
        return tuple(_join(sorted(arg)))
    raise TypeError("Argument may be None, an IntervalSet, an Interval or an "
                    "iterable of Intervals. "
                    "Was {}.".format(type(arg).__name__))


def _create(intervals: t.Iterable[Interval[T]]) -> IntervalSet[T]:
    """Create an IntervalSet directly from a sorted Interval iterable."""
    interval_set = IntervalSet[T](())
    interval_set._intervals = tuple(intervals)
    return interval_set


def _chain_ordered(
    left: t.Iterable[Interval[T]], right: t.Iterable[Interval[T]]
) -> t.Iterator[Interval[T]]:
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


def _complement(intervals: t.Iterable[Interval[T]]) -> t.Iterator[Interval[T]]:
    intervals = iter(intervals)
    try:
        first = next(intervals)
    except StopIteration:
        yield t.cast(Interval[T], UnboundedInterval)
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


def _join(intervals: t.Iterable[Interval[T]]) -> t.Iterator[Interval[T]]:
    """
    Join a possibly overlapping, ordered iterable of intervals, removing any
    empty intervals.

    The intervals must be sorted according to begin primarily and
    end secondarily.

    :param intervals: sorted iterable of intervals
    :returns: merged list of intervals
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


def _intersect(
    left: t.Iterable[Interval[T]], right: t.Iterable[Interval[T]]
) -> t.Iterator[Interval[T]]:
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
