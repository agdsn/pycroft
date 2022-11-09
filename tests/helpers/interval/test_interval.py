import pytest

from pycroft.helpers.interval import (
    closed,
    openclosed,
    closedopen,
    open,
    empty,
    Interval,
    single,
    starting_from,
)


@pytest.mark.parametrize(
    "one, other",
    [
        (closed(0, 0), 0),
        (closed(0, 2), 1),
        (openclosed(None, 0), 0),
        (starting_from(0), 0),
        (open(None, None), 0),
    ],
)
def test_contained(one, other):
    assert other in one
    assert not (other not in one)


@pytest.mark.parametrize('one, other', [
    (empty(0), 0),
    (closedopen(0, 1), 1),
    (openclosed(0, 1), 0),
    (open(0, 1), 1),
])
def test_not_contained(one, other):
    assert other not in one
    assert not (other in one)


def test_begin_greater_than_end():
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
def test_strictly_during(one: Interval, other: Interval, is_strictly_during: bool):
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
def test_during(one: Interval, other: Interval, is_during: bool):
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
def test_strictly_before(one: Interval, other: Interval, strictly_before: bool):
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
def test_before(one: Interval, other: Interval, is_before: bool):
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
def test_strictly_overlaps(one, other, strictly_overlaps):
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
def test_overlaps(one: Interval, other: Interval, overlaps: bool):
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
def test_meets(one, other, meets):
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
def test_starts(one, other, starts):
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
def test_finishes(one, other, finishes):
    assert one.finishes(other) == finishes


@pytest.mark.parametrize('one, other', [
    (closed(0, 0), closed(0, 0)),
    (closed(0, 1), closed(0, 1)),
    (closed(0, None), closed(0, None)),
    (closed(None, 0), closed(None, 0)),
    (closed(None, None), closed(None, None)),
])
def test_equals(one, other):
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
def test_does_not_equal(one, other):
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
def test_length(interval: Interval, expected):
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
def test_empty(interval, should_be_empty):
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
def test_intersection(one, other, expected):
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
def test_join(one, other, expected):
    assert one.join(other) == expected
