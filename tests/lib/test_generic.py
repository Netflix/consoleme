from datetime import datetime
from unittest import TestCase

from consoleme.lib.generic import divide_chunks, is_in_time_range

VALID_RANGE = {
    "days": [0, 1, 2, 3],
    "hour_start": 8,
    "minute_start": 0,
    "hour_end": 14,
    "minute_end": 30,
}


class TestGenericLib(TestCase):
    def test_is_in_time_range_true(self):
        x = datetime(2020, 3, 2, 8, 30)  # Monday
        result = is_in_time_range(x, VALID_RANGE)
        self.assertEqual(result, True)

    def test_is_in_time_range_early(self):
        x = datetime(2020, 3, 2, 7, 30)
        result = is_in_time_range(x, VALID_RANGE)
        self.assertEqual(result, False)

    def test_is_in_time_range_late(self):
        x = datetime(2020, 3, 2, 15, 30)
        result = is_in_time_range(x, VALID_RANGE)
        self.assertEqual(result, False)

    def test_is_in_time_range_wrong_day(self):
        x = datetime(2020, 3, 6, 15, 30)  # Friday
        result = is_in_time_range(x, VALID_RANGE)
        self.assertEqual(result, False)

    def test_divide_chunks(self):
        r = list(divide_chunks(["a", "b", "c", "d", "e"], 3))
        self.assertEqual(r, [["a", "b", "c"], ["d", "e"]])
