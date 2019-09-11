from datetime import date
from unittest import TestCase

from pycroft.helpers.date import diff_month, last_day_of_month


class TestMonths(TestCase):
    def test_date_difference(self):
        for (d1, d2, expected) in [
            (date(2019, 9, 1), date(2019, 8, 31), 1),
            (date(2019, 9, 1), date(2019, 9, 30), 0),
            (date(2019, 9, 1), date(2019, 8, 1), 1),
            (date(2019, 12, 1), date(2018, 12, 1), 12),
            (date(2019, 12, 1), date(2010, 1, 1), 9 * 12 + 11),
        ]:
            with self.subTest(d1=d1, d2=d2, expected=expected):
                self.assertEqual(diff_month(d1, d2), expected)
                self.assertEqual(diff_month(d2, d1), -expected)

    def test_last_date_of_month(self):
        for (d, expected) in [
            (date(2019, 9, 1), 30),
            (date(2019, 8, 1), 31),
            (date(2019, 2, 1), 28),
            (date(2016, 2, 1), 29),
        ]:
            with self.subTest(date=d, expected=expected):
                self.assertEqual(last_day_of_month(d),
                                 d.replace(day=expected))
