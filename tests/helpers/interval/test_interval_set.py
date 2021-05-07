import pytest

from pycroft.helpers.interval import IntervalSet, closed, empty, closedopen, \
    open, openclosed, Interval


@pytest.mark.parametrize('one, other', [
    ([closed(2, 3), closed(2, None), closed(None, 1), closed(1, 3), closed(2, 3),
      closed(-10, None)],
     [closed(None, None)]),
    ([empty(6), closedopen(1, 2), empty(0), closedopen(2, 3), open(4, 5)],
     [closedopen(1, 3), open(4, 5)]),
])
def test_constructor(one: list[Interval], other: list[Interval]):
    assert IntervalSet(one) == IntervalSet(other)


@pytest.mark.parametrize('intervals, expected', [
    ([], open(None, None)),
    ([closed(0, 1), open(2, 3)], [open(None, 0), openclosed(1, 2), closedopen(3, None)]),
    ([closed(None, 0), closed(1, None)], [open(0, 1)]),
])
def test_complement(intervals: list[Interval], expected: IntervalSet):
    assert IntervalSet(intervals).complement() == IntervalSet(expected)


@pytest.mark.parametrize('one, other, expected', [
    ([], [closed(0, 1), open(1, 2)],
     [closed(0, 1), open(1, 2)]),
    ([closed(0, 1), open(1, 2)], [],
     [closed(0, 1), open(1, 2)]),
    ([closed(None, 1), closed(3, 4), open(7, 8)], [open(0, 5), closed(6, 7), closedopen(8, None)],
     [open(None, 5), closed(6, None)]),
])
def test_union(one: list[Interval], other: list[Interval], expected: IntervalSet):
    assert IntervalSet(one).union(IntervalSet(other)) == IntervalSet(expected)


@pytest.mark.parametrize('one, other, expected', [
    ([open(None, None)],
     [openclosed(None, 0), closed(1, 2), closedopen(3, None)],
     [openclosed(None, 0), closed(1, 2), closedopen(3, None)],)
])
def test_intersect(one: list[Interval], other: list[Interval], expected: IntervalSet):
    assert IntervalSet(one).intersect(IntervalSet(other)) == IntervalSet(expected)


@pytest.mark.parametrize('one, other, expected', [
    ([open(None, None)],
     [closed(0, 1), closedopen(2, 3), openclosed(4, 5), open(6, 7)],
     [open(None, 0), open(1, 2), closed(3, 4), openclosed(5, 6), closedopen(7, None)])
])
def test_difference(one: list[Interval], other: list[Interval], expected: IntervalSet):
    assert IntervalSet(one).difference(IntervalSet(other)) == IntervalSet(expected)


@pytest.mark.parametrize('intervals, expected', [
    ([closed(0, 0)], 0),
    ([closed(0, 1)], 1),
    ([closed(0, 0), closed(1, 2), closed(3, 4)], 2),
    ([closed(0, 1), closed(2, None)], None),
    ([closed(None, 0), closed(1, 2)], None),
    ([closed(None, None)], None),
])
def test_length(intervals: list[Interval], expected: IntervalSet):
    assert IntervalSet(intervals).length == expected
