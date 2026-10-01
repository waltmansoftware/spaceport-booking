"""Standalone seed checks: python -m unittest analysis.test_seed."""
import random
import unittest
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from unittest.mock import patch

import seed_original
from seed import CENTRAL, BOOKINGS_PER_SHIP, PERIOD_DAYS, generate_seed


class SeedTests(unittest.TestCase):
    def test_valid_dense_data_across_seasons_and_leap_year(self):
        for anchor in [date(2026, 9, 30), date(2026, 3, 8), date(2026, 11, 1), date(2024, 2, 29)]:
            with self.subTest(anchor=anchor):
                data = generate_seed(anchor)
                self.assertEqual(len(data['ships']), 5)
                self.assertEqual(len(data['bookings']), 6000)
                ids = {ship['id'] for ship in data['ships']}
                groups = defaultdict(list)
                for booking in data['bookings']:
                    self.assertIn(booking['shipId'], ids)
                    self.assertTrue(booking['pilotName'].strip())
                    start = datetime.fromisoformat(booking['startTime'])
                    end = datetime.fromisoformat(booking['endTime'])
                    self.assertEqual(start.utcoffset(), start.astimezone(CENTRAL).utcoffset())
                    self.assertEqual(end.utcoffset(), end.astimezone(CENTRAL).utcoffset())
                    self.assertEqual(start.date(), end.date())
                    self.assertLess(start, end)
                    self.assertGreaterEqual(start.time(), time(6))
                    self.assertLessEqual(end.time(), time(22))
                    groups[booking['shipId']].append((start, end))
                for rows in groups.values():
                    rows.sort()
                    self.assertEqual(len(rows), BOOKINGS_PER_SHIP * 2)
                    supplied = [(start, end) for start, end in rows if start.date() < anchor]
                    aggressive = [(start, end) for start, end in rows if start.date() >= anchor]
                    self.assertEqual(len(supplied), BOOKINGS_PER_SHIP)
                    self.assertEqual(len(aggressive), BOOKINGS_PER_SHIP)
                    self.assertTrue(all(anchor - timedelta(days=PERIOD_DAYS) <= start.date() < anchor
                                        for start, _ in supplied))
                    self.assertTrue(all(anchor <= start.date() < anchor + timedelta(days=PERIOD_DAYS)
                                        for start, _ in aggressive))
                    aggressive_days = {start.date() for start, _ in aggressive}
                    self.assertEqual(len(aggressive_days), 60)
                    for offset in [0, 1, PERIOD_DAYS - 1]:
                        self.assertIn(anchor + timedelta(days=offset), aggressive_days)
                    gaps = [(b[0].astimezone(timezone.utc) - a[1].astimezone(timezone.utc))
                            for a, b in zip(rows, rows[1:])]
                    self.assertTrue(all(gap >= timedelta(minutes=30) for gap in gaps))
                    aggressive_gaps = [(b[0].astimezone(timezone.utc) - a[1].astimezone(timezone.utc))
                                       for a, b in zip(aggressive, aggressive[1:])]
                    self.assertIn(timedelta(minutes=30), aggressive_gaps)
                    self.assertIn(timedelta(minutes=31), aggressive_gaps)
                    self.assertEqual(sum(start.time() == time(6) for start, _ in aggressive), 60)
                    self.assertEqual(sum(end.time() == time(22) for _, end in aggressive), 60)
                    for offset in range(PERIOD_DAYS):
                        day = anchor + timedelta(days=offset)
                        before = datetime.combine(day - timedelta(days=1), time(12), CENTRAL)
                        after = datetime.combine(day, time(12), CENTRAL)
                        if before.utcoffset() != after.utcoffset():
                            self.assertIn(day, aggressive_days)

    def test_fixed_anchor_is_reproducible(self):
        self.assertEqual(generate_seed(date(2026, 9, 30)), generate_seed(date(2026, 9, 30)))

    def test_first_period_matches_supplied_generator(self):
        anchor = date(2026, 9, 30)

        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                value = datetime.combine(anchor, time(12), CENTRAL)
                return value if tz is None else value.astimezone(tz)

        rng = random.Random(42)
        with patch.object(seed_original, 'datetime', FixedDateTime):
            expected = [booking for ship in seed_original.SHIPS
                        for booking in seed_original.generate_bookings(ship['id'], rng)]
        self.assertEqual(generate_seed(anchor)['bookings'][:len(expected)], expected)


if __name__ == '__main__':
    unittest.main()
