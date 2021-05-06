from datetime import date

import pytest

from pycroft.helpers.date import diff_month, last_day_of_month


@pytest.mark.parametrize('d1, d2, expected', [
        (date(2019, 9, 1), date(2019, 8, 31), 1),
        (date(2019, 9, 1), date(2019, 9, 30), 0),
        (date(2019, 9, 1), date(2019, 8, 1), 1),
        (date(2019, 12, 1), date(2018, 12, 1), 12),
        (date(2019, 12, 1), date(2010, 1, 1), 9 * 12 + 11),
])
def test_date_difference(d1, d2, expected):
    assert diff_month(d1, d2) == expected
    assert diff_month(d2, d1) == -expected


@pytest.mark.parametrize('d, expected', [
    (date(2019, 9, 1), 30), (date(2019, 8, 1), 31),
    (date(2019, 2, 1), 28), (date(2016, 2, 1), 29),
])
def test_last_date_of_month(d, expected):
    assert last_day_of_month(d) == d.replace(day=expected)
