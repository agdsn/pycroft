# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import pytest

from pycroft.helpers.interval import (
    Interval, IntervalSet, closed, closedopen, openclosed, open, empty, single)


class Test_Interval:
    @pytest.mark.parametrize('one, other', [
        (closed(0, 0), 0),
        (closed(0, 2), 1),
        (openclosed(None, 0), 0),
        (closedopen(0, None), 0),
        (open(None, None), 0),
    ])
    def test_contained(self, one, other):
        assert other in one
        assert not (other not in one)


    @pytest.mark.parametrize('one, other', [
        (empty(0), 0),
        (closedopen(0, 1), 1),
        (openclosed(0, 1), 0),
        (open(0, 1), 1),
    ])
    def test_not_contained(self, one, other):
        assert other not in one
        assert not (other in one)

    def test_begin_greater_than_end(self):
        with pytest.raises(ValueError):
            Interval(1, 0)

    @pytest.mark.parametrize('one, other, is_strictly_during', [
        (closed(1, 1), closed(0, 2), True),
        (closed(1, 1), closed(None, 2), True),
        (closed(1, 1), closed(0, None), True),
        (closed(1, 1), closed(None, None), True),
        (closed(None, None), closed(None, None), True),

        (closed(1, 1), closed(1, 1), False),
        (closed(1, 1), closed(2, 3), False),
        (closed(1, 1), closed(-1, 0), False),
        (closed(1, 1), closed(2, None), False),
        (closed(1, 1), closed(None, 0), False),
    ])
    def test_strictly_during(self, one: Interval, other: Interval, is_strictly_during: bool):
        assert one.strictly_during(other) == is_strictly_during

    @pytest.mark.parametrize('one, other, is_during', [
        (closed(1, 1), closed(1, 1), True),
        (closed(1, 1), closed(0, 2), True),
        (closed(1, 1), closed(None, 2), True),
        (closed(1, 1), closed(0, None), True),
        (closed(1, 1), closed(None, None), True),
        (closed(None, None), closed(None, None), True),

        (closed(1, 1), closed(2, 3), False),
        (closed(1, 1), closed(-1, 0), False),
        (closed(1, 1), closed(2, None), False),
        (closed(1, 1), closed(None, 0), False),
    ])
    def test_during(self, one: Interval, other: Interval, is_during: bool):
        assert one.during(other) == is_during

    @pytest.mark.parametrize('one, other, strictly_before', [
        (closed(0, 0), closed(1, 1), True),
        (closed(0, 1), closed(2, 3), True),
        (closed(None, 1), closed(2, None), True),

        (closed(0, 0), closed(0, 0), False),
        (closed(0, 1), closed(1, 2), False),
        (closed(1, 2), closed(0, 1), False),
        (closed(0, None), closed(1, 2), False),
        (closed(0, 1), closed(None, 0), False),
        (closed(0, None), closed(None, 0), False),
    ])
    def test_strictly_before(self, one: Interval, other: Interval, strictly_before: bool):
        assert one.strictly_before(other) == strictly_before

    @pytest.mark.parametrize('one, other, is_before', [
        (closed(0, 0), closed(0, 0), True),
        (closed(0, 1), closed(1, 2), True),
        (closed(0, 0), closed(1, 1), True),
        (closed(0, 1), closed(2, 3), True),
        (closed(None, 1), closed(2, None), True),
        (closed(1, 2), closed(0, 1), False),
        (closed(0, None), closed(1, 2), False),
        (closed(0, 1), closed(None, 0), False),
        (closed(0, None), closed(None, 0), False),
    ])
    def test_before(self, one: Interval, other: Interval, is_before: bool):
        assert one.before(other) == is_before

    @pytest.mark.parametrize('one, other, strictly_overlaps', [
        (closed(0, 2), closed(1, 3), True),
        (closed(None, 1), closed(0, None), True),
        (closed(0, None), closed(None, 1), True),
        (closed(0, 1), closed(None, None), True),
        (closed(None, None), closed(0, 1), True),

        (closed(0, 0), closed(0, 0), False),
        (closed(0, 1), closed(1, 2), False),
        (closed(0, 0), closed(1, 1), False),
        (closed(0, 1), closed(2, 3), False),
        (closed(None, 0), closed(1, None), False),
        (closed(1, None), closed(None, 0), False),
    ])
    def test_strictly_overlaps(self, one, other, strictly_overlaps):
        assert one.strictly_overlaps(other) == strictly_overlaps

    @pytest.mark.parametrize('one, other, overlaps', [
        (closed(0, 0), closed(0, 0), True),
        (closed(0, 1), closed(1, 2), True),
        (closed(0, 2), closed(1, 3), True),
        (closed(None, 1), closed(0, None), True),
        (closed(0, None), closed(None, 1), True),
        (closed(0, 1), closed(None, None), True),
        (closed(None, None), closed(0, 1), True),

        (closedopen(0, 1), openclosed(1, 2), False),
        (closedopen(0, 1), closed(1, 2), False),
        (closed(0, 1), openclosed(1, 2), False),
        (closed(0, 0), closed(1, 1), False),
        (closed(0, 1), closed(2, 3), False),
        (closed(None, 0), closed(1, None), False),
        (closed(1, None), closed(None, 0), False),
    ])
    def test_overlaps(self, one: Interval, other: Interval, overlaps: bool):
        assert one.overlaps(other) == overlaps


    @pytest.mark.parametrize('one, other, meets', [
        (closed(0, 0), closed(0, 0), True),
        (closed(0, 1), closed(1, 2), True),
        (closed(None, 0), closed(0, None), True),

        (closed(0, 0), closed(1, 1), False),
        (closed(0, 1), closed(2, 3), False),
        (closed(None, 0), closed(1, None), False),
        (closed(0, 1), closed(None, 2), False),
        (closed(0, None), closed(0, 1), False),
        (closed(0, None), closed(None, 1), False),
    ])
    def test_meets(self, one, other, meets):
        assert one.meets(other) == meets

    @pytest.mark.parametrize('one, other, starts', [
        (closed(0, 0), closed(0, 0), True),
        (closed(0, 1), closed(0, 2), True),
        (closed(None, 0), closed(None, 2), True),

        (closed(0, 1), openclosed(0, 1), False),
        (closed(0, 0), closed(1, 1), False),
        (closed(0, 1), closed(2, 3), False),
        (closed(None, 0), closed(1, None), False),
        (closed(0, 1), closed(None, 2), False),
        (closed(0, None), closed(None, 1), False),
    ])
    def test_starts(self, one, other, starts):
        assert one.starts(other) == starts

    @pytest.mark.parametrize('one, other, finishes', [
        (closed(0, 0), closed(0, 0), True),
        (closed(0, 2), closed(1, 2), True),
        (closed(0, None), closed(1, None), True),

        (closed(0, 0), closed(1, 1), False),
        (closed(0, 1), closedopen(0, 1), False),
        (closed(0, 1), closed(2, 3), False),
        (closed(None, 0), closed(1, None), False),
        (closed(0, 1), closed(None, 2), False),
        (closed(0, None), closed(None, 1), False),
    ])
    def test_finishes(self, one, other, finishes):
        assert one.finishes(other) == finishes

    @pytest.mark.parametrize('one, other', [
        (closed(0, 0), closed(0, 0)),
        (closed(0, 1), closed(0, 1)),
        (closed(0, None), closed(0, None)),
        (closed(None, 0), closed(None, 0)),
        (closed(None, None), closed(None, None)),
    ])
    def test_equals(self, one, other):
        assert one == other
        assert not (one != other)

    @pytest.mark.parametrize('one, other', [
        (closed(0, 0), closed(1, 1)),
        (closed(0, 1), closed(2, 3)),
        (closed(0, 1), closed(0, 2)),
        (closed(0, 2), closed(1, 2)),
        (closed(0, 0), closed(0, None)),
        (closed(1, None), closed(0, None)),
        (closed(None, 0), closed(None, 1)),
    ])
    def test_does_not_equal(self, one, other):
        assert one != other
        assert not (one == other)

    @pytest.mark.parametrize('interval, expected', [
        (open(0, 0), 0),
        (closed(0, 0), 0),
        (open(0, 1), 1),
        (closed(0, 1), 1),
        (closed(0, None), None),
        (closed(None, 0), None),
        (closed(None, None), None),
    ])
    def test_length(self, interval: Interval, expected):
        assert interval.length == expected

    @pytest.mark.parametrize('interval, should_be_empty', [
        (empty(0), True),
        (closedopen(0, 0), True),
        (openclosed(0, 0), True),
        (open(0, 0), True),

        (single(0), False),
        (closed(0, 0), False),
        (closed(0, 1), False),
        (closedopen(0, 1), False),
        (openclosed(0, 1), False),
        (open(0, 1), False),
    ])
    def test_empty(self, interval, should_be_empty):
        assert interval.empty == should_be_empty

    @pytest.mark.parametrize('one, other, expected', [
        (closed(0, 0), closed(0, 0), closed(0, 0)),
        (closed(0, 0), open(0, 0), None),
        (closed(1, 1), closed(0, 2), closed(1, 1)),
        (closed(0, 2), closed(1, 3), closed(1, 2)),
        (closed(0, 3), closed(1, 2), closed(1, 2)),
        (closed(1, 2), closed(0, 3), closed(1, 2)),
        (open(1, 2), closed(0, 3), open(1, 2)),
        (closedopen(1, 2), closed(0, 3), closedopen(1, 2)),
        (openclosed(1, 2), closed(0, 3), openclosed(1, 2)),
        (closed(0, 1), closed(2, 3), None),
        (closed(None, 2), closed(1, None), closed(1, 2)),
        (closed(1, 2), closed(None, None), closed(1, 2)),
        (closed(None, None), closed(None, None), closed(None, None)),
    ])
    def test_intersection(self, one, other, expected):
        assert one.intersect(other) == expected

    @pytest.mark.parametrize('one, other, expected', [
        (closed(0, 0), closed(0, 0), closed(0, 0)),
        (closed(0, 0), closed(0, 1), closed(0, 1)),
        (closed(0, 1), closed(1, 2), closed(0, 2)),
        (closedopen(0, 1), closed(1, 2), closed(0, 2)),
        (closed(0, 0), closed(1, 1), None),
        (closed(None, 0), closed(1, None), None),
        (closed(None, None), closed(1, 2), closed(None, None)),
        (closed(None, 0), closed(0, None), closed(None, None)),
        (closed(None, None), closed(None, None), closed(None, None)),
    ])
    def test_join(self, one, other, expected):
        assert one.join(other) == expected


class TestIntervalSet:
    def test_sort_join(self):
        assert IntervalSet([
            closed(2, 3), closed(2, None), closed(None, 1), closed(1, 3), closed(2, 3), closed(-10, None)
        ]) == IntervalSet([
            closed(None, None)
        ])
        assert IntervalSet([empty(6), closedopen(1, 2), empty(0), closedopen(2, 3), open(4, 5)]) \
            == IntervalSet([closedopen(1, 3), open(4, 5)])

    @pytest.mark.parametrize('intervals, expected', [
        ([], open(None, None)),
        ([closed(0, 1), open(2, 3)], [open(None, 0), openclosed(1, 2), closedopen(3, None)]),
        ([closed(None, 0), closed(1, None)], [open(0, 1)]),
    ])
    def test_complement(self, intervals, expected):
        assert IntervalSet(intervals).complement() == IntervalSet(expected)

    @pytest.mark.parametrize('one, other, expected', [
        ([], [closed(0, 1), open(1, 2)],
         [closed(0, 1), open(1, 2)]),
        ([closed(0, 1), open(1, 2)], [],
         [closed(0, 1), open(1, 2)]),
        ([closed(None, 1), closed(3, 4), open(7, 8)], [open(0, 5), closed(6, 7), closedopen(8, None)],
         [open(None, 5), closed(6, None)]),
    ])
    def test_union(self, one, other, expected):
        assert IntervalSet(one).union(IntervalSet(other)) == IntervalSet(expected)

    @pytest.mark.parametrize('one, other, expected', [
        ([open(None, None)],
         [openclosed(None, 0), closed(1, 2), closedopen(3, None)],
         [openclosed(None, 0), closed(1, 2), closedopen(3, None)],)
    ])
    def test_intersect(self, one, other, expected):
        assert IntervalSet(one).intersect(IntervalSet(other)) == IntervalSet(expected)


    @pytest.mark.parametrize('one, other, expected', [
        ([open(None, None)],
         [closed(0, 1), closedopen(2, 3), openclosed(4, 5), open(6, 7)],
        [open(None, 0), open(1, 2), closed(3, 4), openclosed(5, 6), closedopen(7, None)])
    ])
    def test_difference(self, one, other, expected):
        assert IntervalSet(one).difference(IntervalSet(other)) == IntervalSet(expected)

    @pytest.mark.parametrize('intervals, expected', [
        ([closed(0, 0)], 0),
        ([closed(0, 1)], 1),
        ([closed(0, 0), closed(1, 2), closed(3, 4)], 2),
        ([closed(0, 1), closed(2, None)], None),
        ([closed(None, 0), closed(1, 2)], None),
        ([closed(None, None)], None),
    ])
    def test_length(self, intervals, expected):
        assert IntervalSet(intervals).length == expected


class TestTypeMangling:
    def test_type_mangling(self):
        # TODO one test per assertion and `target` / `base` as fixtures
        target = IntervalSet([closed(0, 1)])
        # Creation
        assert target == IntervalSet(closed(0, 1))
        assert target == IntervalSet([closed(0, 1)])
        with pytest.raises(TypeError):
            IntervalSet(0)
        # Union
        base = IntervalSet(())
        assert target == base | IntervalSet(closed(0, 1))
        assert target == base | closed(0, 1)
        assert target == base | [closed(0, 1)]
        # Intersection
        base = target | closed(1, 2)
        assert target == base & IntervalSet(openclosed(0, 1))
        assert target == base & openclosed(0, 1)
        assert target == base & [openclosed(0, 1)]
        # Difference
        assert target == base - IntervalSet(openclosed(1, 2))
        assert target == base - openclosed(1, 2)
        assert target == base - [openclosed(1, 2)]
