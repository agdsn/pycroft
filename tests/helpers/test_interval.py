import unittest
from pycroft.helpers.interval import Interval


class Test_010_Interval(unittest.TestCase):
    def assertIntervalOperationTrue(self, relation, args):
        self.assertIntervalOperationEquals(
            relation, map(lambda arg: (arg, True), args)
        )

    def assertIntervalOperationFalse(self, relation, args):
        self.assertIntervalOperationEquals(
            relation, map(lambda arg: (arg, False), args)
        )

    def assertIntervalOperationEquals(self, operation, args_and_expected):
        """
        :param callable operation:
        :param iterable[iterable[Interval], unknown)] args_and_expected:
        """
        for intervals, expected in args_and_expected:
            intervals = map(lambda args: Interval(*args), intervals)
            got = operation(*intervals)
            assert got == expected, (
                "Evaluating {0}({1}) failed: expected {2}, got {3}".format(
                    operation.__name__, ', '.join(map(str, intervals)),
                    expected, got
                )
            )

    def test_0010_begin_greater_than_end(self):
        self.assertRaises(ValueError, Interval, 1, 0)

    def test_0020_strictly_during(self):
        self.assertIntervalOperationTrue(Interval.strictly_during, [
            ((1, 1), (0, 2)),
            ((1, 1), (None, 2)),
            ((1, 1), (0, None)),
            ((1, 1), (None, None)),
            ((None, None), (None, None)),
        ])
        self.assertIntervalOperationFalse(Interval.strictly_during, [
            ((1, 1), (1, 1)),
            ((1, 1), (2, 3)),
            ((1, 1), (-1, 0)),
            ((1, 1), (2, None)),
            ((1, 1), (None, 0)),
        ])

    def test_0030_during(self):
        self.assertIntervalOperationTrue(Interval.during, [
            ((1, 1), (1, 1)),
            ((1, 1), (0, 2)),
            ((1, 1), (None, 2)),
            ((1, 1), (0, None)),
            ((1, 1), (None, None)),
            ((None, None), (None, None)),
        ])
        self.assertIntervalOperationFalse(Interval.during, [
            ((1, 1), (2, 3)),
            ((1, 1), (-1, 0)),
            ((1, 1), (2, None)),
            ((1, 1), (None, 0)),
        ])

    def test_0040_strictly_before(self):
        self.assertIntervalOperationTrue(Interval.__lt__, [
            ((0, 0), (1, 1)),
            ((0, 1), (2, 3)),
            ((None, 1), (2, None)),
        ])
        self.assertIntervalOperationFalse(Interval.__lt__, [
            ((0, 0), (0, 0)),
            ((0, 1), (1, 2)),
            ((1, 2), (0, 1)),
            ((0, None), (1, 2)),
            ((0, 1), (None, 0)),
            ((0, None), (None, 0)),
        ])

    def test_0050_before(self):
        self.assertIntervalOperationTrue(Interval.__le__, [
            ((0, 0), (0, 0)),
            ((0, 1), (1, 2)),
            ((0, 0), (1, 1)),
            ((0, 1), (2, 3)),
            ((None, 1), (2, None)),
        ])
        self.assertIntervalOperationFalse(Interval.__le__, [
            ((1, 2), (0, 1)),
            ((0, None), (1, 2)),
            ((0, 1), (None, 0)),
            ((0, None), (None, 0)),
        ])

    def test_0060_overlaps_strictly(self):
        self.assertIntervalOperationTrue(Interval.overlaps_strictly, [
            ((0, 2), (1, 3)),
            ((None, 1), (0, None)),
            ((0, None), (None, 1)),
            ((0, 1), (None, None)),
            ((None, None), (0, 1)),
        ])
        self.assertIntervalOperationFalse(Interval.overlaps_strictly, [
            ((0, 0), (0, 0)),
            ((0, 1), (1, 2)),
            ((0, 0), (1, 1)),
            ((0, 1), (2, 3)),
            ((None, 0), (1, None)),
            ((1, None), (None, 0)),
        ])

    def test_0070_overlaps(self):
        self.assertIntervalOperationTrue(Interval.overlaps, [
            ((0, 0), (0, 0)),
            ((0, 1), (1, 2)),
            ((0, 2), (1, 3)),
            ((None, 1), (0, None)),
            ((0, None), (None, 1)),
            ((0, 1), (None, None)),
            ((None, None), (0, 1)),
        ])
        self.assertIntervalOperationFalse(Interval.overlaps, [
            ((0, 0), (1, 1)),
            ((0, 1), (2, 3)),
            ((None, 0), (1, None)),
            ((1, None), (None, 0)),
        ])

    def test_0080_meets(self):
        self.assertIntervalOperationTrue(Interval.meets, [
            ((0, 0), (0, 0)),
            ((0, 1), (1, 2)),
            ((None, 0), (0, None)),
        ])
        self.assertIntervalOperationFalse(Interval.meets, [
            ((0, 0), (1, 1)),
            ((0, 1), (2, 3)),
            ((None, 0), (1, None)),
            ((0, 1), (None, 2)),
            ((0, None), (0, 1)),
            ((0, None), (None, 1)),
        ])

    def test_0090_starts(self):
        self.assertIntervalOperationTrue(Interval.starts, [
            ((0, 0), (0, 0)),
            ((0, 1), (0, 2)),
            ((None, 0), (None, 2)),
        ])
        self.assertIntervalOperationFalse(Interval.starts, [
            ((0, 0), (1, 1)),
            ((0, 1), (2, 3)),
            ((None, 0), (1, None)),
            ((0, 1), (None, 2)),
            ((0, None), (None, 1)),
        ])

    def test_0100_finishes(self):
        self.assertIntervalOperationTrue(Interval.finishes, [
            ((0, 0), (0, 0)),
            ((0, 2), (1, 2)),
            ((0, None), (1, None)),
        ])
        self.assertIntervalOperationFalse(Interval.finishes, [
            ((0, 0), (1, 1)),
            ((0, 1), (2, 3)),
            ((None, 0), (1, None)),
            ((0, 1), (None, 2)),
            ((0, None), (None, 1)),
        ])

    def test_0110_equals(self):
        self.assertIntervalOperationTrue(Interval.__eq__, [
            ((0, 0), (0, 0)),
            ((0, 1), (0, 1)),
            ((0, None), (0, None)),
            ((None, 0), (None, 0)),
            ((None, None), (None, None)),
        ])
        self.assertIntervalOperationFalse(Interval.__eq__, [
            ((0, 0), (1, 1)),
            ((0, 1), (2, 3)),
            ((0, 1), (0, 2)),
            ((0, 2), (1, 2)),
            ((0, 0), (0, None)),
            ((1, None), (0, None)),
            ((None, 0), (None, 1)),
        ])

    def test_0120_length(self):
        self.assertIntervalOperationEquals(Interval.length, [
            ([(0, 0)], 0),
            ([(0, 1)], 1),
            ([(0, None)], None),
            ([(None, 0)], None),
            ([(None, None)], None),
        ])

    def test_0130_intersect(self):
        self.assertIntervalOperationEquals(Interval.intersect, [
            (((0, 0), (0, 0)), Interval(0, 0)),
            (((1, 1), (0, 2)), Interval(1, 1)),
            (((0, 2), (1, 3)), Interval(1, 2)),
            (((0, 3), (1, 2)), Interval(1, 2)),
            (((1, 2), (0, 3)), Interval(1, 2)),
            (((0, 1), (2, 3)), None),
            (((None, 2), (1, None)), Interval(1, 2)),
            (((1, 2), (None, None)), Interval(1, 2)),
            (((None, None), (None, None)), Interval(None, None)),
        ])
