"""Standalone seed checks: python -m unittest analysis.test_seed."""
import random
import unittest
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from unittest.mock import patch

import seed_original
from seed import (
    CENTRAL,
    FUTURE_DAYS,
    HISTORICAL_BOOKINGS_PER_SHIP,
    HISTORY_DAYS,
    MAX_FUTURE_BOOKINGS_PER_SHIP_DAY,
    generate_seed,
)


class SeedTests(unittest.TestCase):
    def test_valid_history_and_light_bookings_today_through_next_week(self):
        for anchor in [date(2026, 10, 1), date(2026, 3, 8), date(2026, 11, 1), date(2024, 2, 29)]:
            with self.subTest(anchor=anchor):
                data = generate_seed(anchor, random_seed=42)
                self.assertEqual(len(data['ships']), 5)
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
                    historical = [(start, end) for start, end in rows if start.date() < anchor]
                    future = [(start, end) for start, end in rows if start.date() >= anchor]
                    self.assertEqual(len(historical), HISTORICAL_BOOKINGS_PER_SHIP)
                    self.assertTrue(all(
                        anchor - timedelta(days=HISTORY_DAYS) <= start.date() < anchor
                        for start, _ in historical
                    ))
                    self.assertTrue(all(
                        anchor <= start.date() <= anchor + timedelta(days=FUTURE_DAYS)
                        for start, _ in future
                    ))
                    by_day = defaultdict(list)
                    for start, end in future:
                        by_day[start.date()].append((start, end))
                    self.assertEqual(
                        set(by_day),
                        {anchor + timedelta(days=offset) for offset in range(FUTURE_DAYS + 1)},
                    )
                    self.assertTrue(all(
                        1 <= len(day_rows) <= MAX_FUTURE_BOOKINGS_PER_SHIP_DAY
                        for day_rows in by_day.values()
                    ))
                    gaps = [
                        b[0].astimezone(timezone.utc) - a[1].astimezone(timezone.utc)
                        for a, b in zip(rows, rows[1:])
                    ]
                    self.assertTrue(all(gap >= timedelta(minutes=30) for gap in gaps))

    def test_explicit_random_seed_is_reproducible(self):
        anchor = date(2026, 10, 1)
        self.assertEqual(
            generate_seed(anchor, random_seed=42),
            generate_seed(anchor, random_seed=42),
        )
        self.assertNotEqual(
            generate_seed(anchor, random_seed=1),
            generate_seed(anchor, random_seed=2),
        )

    def test_historical_period_can_reproduce_supplied_generator(self):
        anchor = date(2026, 10, 1)

        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                value = datetime.combine(anchor, time(12), CENTRAL)
                return value if tz is None else value.astimezone(tz)

        rng = random.Random(42)
        with patch.object(seed_original, 'datetime', FixedDateTime):
            expected = [
                booking
                for ship in seed_original.SHIPS
                for booking in seed_original.generate_bookings(ship['id'], rng)
            ]
        actual = generate_seed(anchor, random_seed=42)['bookings'][:len(expected)]
        self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
