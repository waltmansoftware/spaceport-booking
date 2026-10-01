"""Verify occupancy math independently of Django and generated seed files."""
import unittest
from datetime import date
from analysis.seed_utilization import analyze


class UtilizationTests(unittest.TestCase):
    def calculate(self, intervals):
        return analyze({'ships': [{'id': 1}], 'bookings': [
            {'shipId': 1, 'startTime': start, 'endTime': end} for start, end in intervals
        ]}, date(2026, 9, 30), date(2026, 10, 1))

    def test_trailing_refueling_and_closing_clip(self):
        result = self.calculate([
            ('2026-09-30T06:00:00-05:00', '2026-09-30T07:00:00-05:00'),
            ('2026-09-30T07:30:00-05:00', '2026-09-30T08:30:00-05:00'),
            ('2026-09-30T21:00:00-05:00', '2026-09-30T22:00:00-05:00'),
        ])
        self.assertEqual(result['capacity_hours'], 16)
        self.assertEqual(result['flight_hours'], 3)
        self.assertEqual(result['refueling_hours_within_open_hours'], 1)
        self.assertEqual(result['busy_hours'], 4)
        self.assertEqual(result['available_percent'], 75)

    def test_union_does_not_double_count_occupied_minutes(self):
        result = self.calculate([
            ('2026-09-30T06:00:00-05:00', '2026-09-30T07:00:00-05:00'),
            ('2026-09-30T06:30:00-05:00', '2026-09-30T07:30:00-05:00'),
        ])
        self.assertEqual(result['flight_hours'], 1.5)
        self.assertEqual(result['busy_hours'], 2)

    def test_central_date_and_exclusive_window_end(self):
        result = self.calculate([
            ('2026-10-01T02:00:00+00:00', '2026-10-01T03:00:00+00:00'),
            ('2026-10-01T06:00:00-05:00', '2026-10-01T07:00:00-05:00'),
        ])
        self.assertEqual(result['bookings_in_window'], 1)
        self.assertEqual(result['bookings_on_or_after_end'], 1)
        self.assertEqual(result['flight_hours'], 1)
        self.assertEqual(result['busy_hours'], 1)


if __name__ == '__main__':
    unittest.main()
