# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from itertools import imap
import unittest
import operator
from pycroft.helpers.interval import (
    Interval, IntervalSet, closed, closedopen, openclosed, open, empty, single)


class IntervalTestCase(unittest.TestCase):
    def assertCallTrue(self, relation, args):
        self.assertCallEquals(
            relation, imap(lambda arg: (arg, True), args)
        )

    def assertCallFalse(self, relation, args):
        self.assertCallEquals(
            relation, imap(lambda arg: (arg, False), args)
        )

    def assertCallEquals(self, method, args_and_expected):
        """
        :param callable method:
        :param iterable[iterable[(T, T)], S)] args_and_expected:
        """
        for args, expected in args_and_expected:
            got = method(*args)
            assert got == expected, (
                "Evaluating {0}({1}) failed: expected {2}, got {3}".format(
                    getattr(method, '__name__', str(method)),
                    ', '.join(imap(str, args)),
                    expected, got
                )
            )


class Test_Interval(IntervalTestCase):

    def test_begin_greater_than_end(self):
        self.assertRaises(ValueError, Interval, 1, 0)

    def test_contains_operator(self):
        self.assertCallTrue(operator.contains, [
            (closed(0, 0), 0),
            (closed(0, 2), 1),
            (openclosed(None, 0), 0),
            (closedopen(0, None), 0),
            (open(None, None), 0),
        ])
        self.assertCallFalse(operator.contains, [
            (empty(0), 0),
            (closedopen(0, 1), 1),
            (openclosed(0, 1), 0),
            (open(0, 1), 1),
        ])

    def test_strictly_during(self):
        self.assertCallTrue(Interval.strictly_during, [
            (closed(1, 1), closed(0, 2)),
            (closed(1, 1), closed(None, 2)),
            (closed(1, 1), closed(0, None)),
            (closed(1, 1), closed(None, None)),
            (closed(None, None), closed(None, None)),
        ])
        self.assertCallFalse(Interval.strictly_during, [
            (closed(1, 1), closed(1, 1)),
            (closed(1, 1), closed(2, 3)),
            (closed(1, 1), closed(-1, 0)),
            (closed(1, 1), closed(2, None)),
            (closed(1, 1), closed(None, 0)),
        ])

    def test_during(self):
        self.assertCallTrue(Interval.during, [
            (closed(1, 1), closed(1, 1)),
            (closed(1, 1), closed(0, 2)),
            (closed(1, 1), closed(None, 2)),
            (closed(1, 1), closed(0, None)),
            (closed(1, 1), closed(None, None)),
            (closed(None, None), closed(None, None)),
        ])
        self.assertCallFalse(Interval.during, [
            (closed(1, 1), closed(2, 3)),
            (closed(1, 1), closed(-1, 0)),
            (closed(1, 1), closed(2, None)),
            (closed(1, 1), closed(None, 0)),
        ])

    def test_strictly_before(self):
        self.assertCallTrue(Interval.strictly_before, [
            (closed(0, 0), closed(1, 1)),
            (closed(0, 1), closed(2, 3)),
            (closed(None, 1), closed(2, None)),
        ])
        self.assertCallFalse(Interval.strictly_before, [
            (closed(0, 0), closed(0, 0)),
            (closed(0, 1), closed(1, 2)),
            (closed(1, 2), closed(0, 1)),
            (closed(0, None), closed(1, 2)),
            (closed(0, 1), closed(None, 0)),
            (closed(0, None), closed(None, 0)),
        ])

    def test_before(self):
        self.assertCallTrue(Interval.before, [
            (closed(0, 0), closed(0, 0)),
            (closed(0, 1), closed(1, 2)),
            (closed(0, 0), closed(1, 1)),
            (closed(0, 1), closed(2, 3)),
            (closed(None, 1), closed(2, None)),
        ])
        self.assertCallFalse(Interval.before, [
            (closed(1, 2), closed(0, 1)),
            (closed(0, None), closed(1, 2)),
            (closed(0, 1), closed(None, 0)),
            (closed(0, None), closed(None, 0)),
        ])

    def test_strictly_overlaps(self):
        self.assertCallTrue(Interval.strictly_overlaps, [
            (closed(0, 2), closed(1, 3)),
            (closed(None, 1), closed(0, None)),
            (closed(0, None), closed(None, 1)),
            (closed(0, 1), closed(None, None)),
            (closed(None, None), closed(0, 1)),
        ])
        self.assertCallFalse(Interval.strictly_overlaps, [
            (closed(0, 0), closed(0, 0)),
            (closed(0, 1), closed(1, 2)),
            (closed(0, 0), closed(1, 1)),
            (closed(0, 1), closed(2, 3)),
            (closed(None, 0), closed(1, None)),
            (closed(1, None), closed(None, 0)),
        ])

    def test_overlaps(self):
        self.assertCallTrue(Interval.overlaps, [
            (closed(0, 0), closed(0, 0)),
            (closed(0, 1), closed(1, 2)),
            (closed(0, 2), closed(1, 3)),
            (closed(None, 1), closed(0, None)),
            (closed(0, None), closed(None, 1)),
            (closed(0, 1), closed(None, None)),
            (closed(None, None), closed(0, 1)),
        ])
        self.assertCallFalse(Interval.overlaps, [
            (closedopen(0, 1), openclosed(1, 2)),
            (closedopen(0, 1), closed(1, 2)),
            (closed(0, 1), openclosed(1, 2)),
            (closed(0, 0), closed(1, 1)),
            (closed(0, 1), closed(2, 3)),
            (closed(None, 0), closed(1, None)),
            (closed(1, None), closed(None, 0)),
        ])

    def test_meets(self):
        self.assertCallTrue(Interval.meets, [
            (closed(0, 0), closed(0, 0)),
            (closed(0, 1), closed(1, 2)),
            (closed(None, 0), closed(0, None)),
        ])
        self.assertCallFalse(Interval.meets, [
            (closed(0, 0), closed(1, 1)),
            (closed(0, 1), closed(2, 3)),
            (closed(None, 0), closed(1, None)),
            (closed(0, 1), closed(None, 2)),
            (closed(0, None), closed(0, 1)),
            (closed(0, None), closed(None, 1)),
        ])

    def test_starts(self):
        self.assertCallTrue(Interval.starts, [
            (closed(0, 0), closed(0, 0)),
            (closed(0, 1), closed(0, 2)),
            (closed(None, 0), closed(None, 2)),
        ])
        self.assertCallFalse(Interval.starts, [
            (closed(0, 1), openclosed(0, 1)),
            (closed(0, 0), closed(1, 1)),
            (closed(0, 1), closed(2, 3)),
            (closed(None, 0), closed(1, None)),
            (closed(0, 1), closed(None, 2)),
            (closed(0, None), closed(None, 1)),
        ])

    def test_finishes(self):
        self.assertCallTrue(Interval.finishes, [
            (closed(0, 0), closed(0, 0)),
            (closed(0, 2), closed(1, 2)),
            (closed(0, None), closed(1, None)),
        ])
        self.assertCallFalse(Interval.finishes, [
            (closed(0, 0), closed(1, 1)),
            (closed(0, 1), closedopen(0, 1)),
            (closed(0, 1), closed(2, 3)),
            (closed(None, 0), closed(1, None)),
            (closed(0, 1), closed(None, 2)),
            (closed(0, None), closed(None, 1)),
        ])

    def test_equals(self):
        self.assertCallTrue(Interval.__eq__, [
            (closed(0, 0), closed(0, 0)),
            (closed(0, 1), closed(0, 1)),
            (closed(0, None), closed(0, None)),
            (closed(None, 0), closed(None, 0)),
            (closed(None, None), closed(None, None)),
        ])
        self.assertCallFalse(Interval.__eq__, [
            (closed(0, 0), closed(1, 1)),
            (closed(0, 1), closed(2, 3)),
            (closed(0, 1), closed(0, 2)),
            (closed(0, 2), closed(1, 2)),
            (closed(0, 0), closed(0, None)),
            (closed(1, None), closed(0, None)),
            (closed(None, 0), closed(None, 1)),
        ])

    def test_length(self):
        self.assertCallEquals(operator.attrgetter("length"), [
            ([open(0, 0)], 0),
            ([closed(0, 0)], 0),
            ([open(0, 1)], 1),
            ([closed(0, 1)], 1),
            ([closed(0, None)], None),
            ([closed(None, 0)], None),
            ([closed(None, None)], None),
        ])

    def test_empty(self):
        self.assertCallTrue(operator.attrgetter("empty"), [
            [empty(0)],
            [closedopen(0, 0)],
            [openclosed(0, 0)],
            [open(0, 0)],
        ])
        self.assertCallFalse(operator.attrgetter("empty"), [
            [single(0)],
            [closed(0, 0)],
            [closed(0, 1)],
            [closedopen(0, 1)],
            [openclosed(0, 1)],
            [open(0, 1)],
        ])

    def test_intersect(self):
        self.assertCallEquals(Interval.intersect, [
            ((closed(0, 0), closed(0, 0)), closed(0, 0)),
            ((closed(0, 0), open(0, 0)), None),
            ((closed(1, 1), closed(0, 2)), closed(1, 1)),
            ((closed(0, 2), closed(1, 3)), closed(1, 2)),
            ((closed(0, 3), closed(1, 2)), closed(1, 2)),
            ((closed(1, 2), closed(0, 3)), closed(1, 2)),
            ((open(1, 2), closed(0, 3)), open(1, 2)),
            ((closedopen(1, 2), closed(0, 3)), closedopen(1, 2)),
            ((openclosed(1, 2), closed(0, 3)), openclosed(1, 2)),
            ((closed(0, 1), closed(2, 3)), None),
            ((closed(None, 2), closed(1, None)), closed(1, 2)),
            ((closed(1, 2), closed(None, None)), closed(1, 2)),
            ((closed(None, None), closed(None, None)), closed(None, None)),
        ])

    def test_join(self):
        self.assertCallEquals(Interval.join, [
            ((closed(0, 0), closed(0, 0)), closed(0, 0)),
            ((closed(0, 0), closed(0, 1)), closed(0, 1)),
            ((closed(0, 1), closed(1, 2)), closed(0, 2)),
            ((closedopen(0, 1), closed(1, 2)), closed(0, 2)),
            ((closed(0, 0), closed(1, 1)), None),
            ((closed(None, 0), closed(1, None)), None),
            ((closed(None, None), closed(1, 2)), closed(None, None)),
            ((closed(None, 0), closed(0, None)), closed(None, None)),
            ((closed(None, None), closed(None, None)), closed(None, None)),
        ])


class Test_0200_IntervalSet(unittest.TestCase):
    @classmethod
    def assertIntervalSetMethodEquals(cls, method, args_and_expected):
        """
        :param callable method:
        :param iterable[iterable[IntervalSet], unknown)] args_and_expected:
        """
        for args, expected in args_and_expected:
            args = map(lambda intervals: IntervalSet(intervals), args)
            got = method(*args)
            assert got == expected, (
                "Evaluating {0}({1}) failed: expected {2}, got {3}".format(
                    method.__name__, ', '.join(map(str, args)),
                    expected, got
                )
            )

    @classmethod
    def assertIntervalSetOperationEquals(cls, operation, args_and_expected):
        """
        :param callable operation:
        :param iterable[iterable[IntervalSet], unknown)] args_and_expected:
        """
        cls.assertIntervalSetMethodEquals(operation, (
            (args, IntervalSet(expected)) for args, expected in args_and_expected
        ))

    def test_sort_join(self):
        self.assertEqual(
            IntervalSet([closed(2, 3), closed(2, None), closed(None, 1), closed(1, 3), closed(2, 3), closed(-10, None)]),
            IntervalSet([closed(None, None)])
        )
        self.assertEqual(
            IntervalSet([empty(6), closedopen(1, 2), empty(0), closedopen(2, 3), open(4, 5)]),
            IntervalSet([closedopen(1, 3), open(4, 5)]),
        )

    def test_complement(self):
        self.assertIntervalSetOperationEquals(IntervalSet.complement, [
            ([[]], open(None, None)),
            ([[closed(0, 1), open(2, 3)]], [open(None, 0), openclosed(1, 2), closedopen(3, None)]),
            ([[closed(None, 0), closed(1, None)]], ([open(0, 1)])),
        ])

    def test_union(self):
        self.assertIntervalSetOperationEquals(IntervalSet.union, [
            ([[], [closed(0, 1), open(1, 2)]], [closed(0, 1), open(1, 2)]),
            ([[closed(0, 1), open(1, 2)], []], [closed(0, 1), open(1, 2)]),
            ([[closed(None, 1), closed(3, 4), open(7, 8)],
              [open(0, 5), closed(6, 7), closedopen(8, None)]],
             [open(None, 5), closed(6, None)]),
        ])

    def test_intersect(self):
        self.assertIntervalSetOperationEquals(IntervalSet.intersect, [
            ([[open(None, None)], [openclosed(None, 0), closed(1, 2), closedopen(3, None)]], [openclosed(None, 0), closed(1, 2), closedopen(3, None)]),
        ])

    def test_difference(self):
        self.assertIntervalSetOperationEquals(IntervalSet.difference, [
            ([[open(None, None)], [closed(0, 1), closedopen(2, 3), openclosed(4, 5), open(6, 7)]], [open(None, 0), open(1, 2), closed(3, 4), openclosed(5, 6), closedopen(7, None)]),
        ])

    def test_length(self):
        self.assertIntervalSetMethodEquals(IntervalSet.length, [
            ([[closed(0, 0)]], 0),
            ([[closed(0, 1)]], 1),
            ([[closed(0, 0), closed(1, 2), closed(3, 4)]], 2),
            ([[closed(0, 1), closed(2, None)]], None),
            ([[closed(None, 0), closed(1, 2)]], None),
            ([[closed(None, None)]], None),
        ])

    def test_type_mangling(self):
        target = IntervalSet([closed(0, 1)])
        # Creation
        self.assertEqual(target, IntervalSet(closed(0, 1)))
        self.assertEqual(target, IntervalSet([closed(0, 1)]))
        self.assertRaises(TypeError, IntervalSet, 0)
        # Union
        base = IntervalSet(())
        self.assertEqual(target, base | IntervalSet(closed(0, 1)))
        self.assertEqual(target, base | closed(0, 1))
        self.assertEqual(target, base | [closed(0, 1)])
        # Intersection
        base = target | closed(1, 2)
        self.assertEqual(target, base & IntervalSet(openclosed(0, 1)))
        self.assertEqual(target, base & openclosed(0, 1))
        self.assertEqual(target, base & [openclosed(0, 1)])
        # Difference
        self.assertEqual(target, base - IntervalSet(openclosed(1, 2)))
        self.assertEqual(target, base - openclosed(1, 2))
        self.assertEqual(target, base - [openclosed(1, 2)])
