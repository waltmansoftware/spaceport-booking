"""Generate two consecutive years of valid bookings.

    python seed.py > seed.json
    python seed.py --today 2026-09-30 > seed.json

The first 365-day period reproduces the supplied generator's scheduling pattern.
The second 365-day period uses the aggressive boundary-focused pattern. The
anchor date is the first day of the aggressive period. Does not modify the DB.
"""
import argparse
import json
import random
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

# Keep the supplied fleet and pilot names without duplicating them.
from seed_original import PILOTS, SHIPS

CENTRAL = ZoneInfo('America/Chicago')
PERIOD_DAYS = 365
BOOKINGS_PER_SHIP = 600
BOOKINGS_PER_DAY = 10
REFUEL_BUFFER = timedelta(minutes=30)


def aggressive_schedule_dates(period_start, rng):
    """Choose 60 dense days throughout the second 365-day period."""
    days = [period_start + timedelta(days=i) for i in range(PERIOD_DAYS)]
    required = {days[0], days[1], days[-1]}
    for day in days:
        noon = datetime.combine(day, time(12), CENTRAL)
        previous_noon = datetime.combine(day - timedelta(days=1), time(12), CENTRAL)
        if noon.utcoffset() != previous_noon.utcoffset():
            required.add(day)
    count = BOOKINGS_PER_SHIP // BOOKINGS_PER_DAY
    remaining = [day for day in days if day not in required]
    return sorted(required | set(rng.sample(remaining, count - len(required))))


def generate_supplied_bookings(ship_id, period_start, rng):
    """Reproduce the supplied generator's timing inside the first period."""
    bookings = []
    cursor = None
    day = period_start
    period_end = period_start + timedelta(days=PERIOD_DAYS)

    while len(bookings) < BOOKINGS_PER_SHIP and day < period_end:
        opening = datetime.combine(day, time(6), CENTRAL)
        closing = datetime.combine(day, time(22), CENTRAL)

        if cursor is None or cursor < opening:
            cursor = opening
        cursor += timedelta(minutes=rng.choice([30, 60, 90, 120, 240, 480]))

        if cursor >= closing:
            day += timedelta(days=1)
            cursor = None
            continue

        end = cursor + timedelta(minutes=rng.choice([60, 90, 120, 150, 180, 240]))
        if end > closing:
            day += timedelta(days=1)
            cursor = None
            continue

        bookings.append({
            'shipId': ship_id,
            'pilotName': rng.choice(PILOTS),
            'startTime': cursor.isoformat(),
            'endTime': end.isoformat(),
        })
        cursor = end + REFUEL_BUFFER

    if len(bookings) != BOOKINGS_PER_SHIP:
        raise RuntimeError('Supplied pattern did not reach its booking quota within the first period.')
    return bookings


def generate_aggressive_bookings(ship_id, days, rng):
    """Generate ten tightly packed flights on every selected second-year day."""
    bookings = []
    for day in days:
        cursor = datetime.combine(day, time(6), CENTRAL)
        closing = datetime.combine(day, time(22), CENTRAL)
        for index in range(BOOKINGS_PER_DAY):
            # First pair is 06:00–07:00 and 07:30–08:30 on every selected day.
            duration = 60 if index < 2 else rng.choice([30, 45, 60])
            end = cursor + timedelta(minutes=duration)
            if index == BOOKINGS_PER_DAY - 1:
                end = closing
            bookings.append({
                'shipId': ship_id,
                'pilotName': rng.choice(PILOTS),
                'startTime': cursor.isoformat(),
                'endTime': end.isoformat(),
            })
            # Refuel exactly once. Extra idle time can be zero; never add a
            # second mandatory random delay before starting the next flight.
            extra_idle = 0 if index == 0 else 1 if index == 1 else rng.choice([0, 0, 0, 1])
            cursor = end + REFUEL_BUFFER + timedelta(minutes=extra_idle)
    return bookings


def generate_seed(today):
    supplied_rng = random.Random(42)
    supplied_start = today - timedelta(days=PERIOD_DAYS)
    supplied = [booking for ship in SHIPS for booking in generate_supplied_bookings(
        ship['id'], supplied_start, supplied_rng)]

    aggressive_rng = random.Random(43)
    aggressive_days = aggressive_schedule_dates(today, aggressive_rng)
    aggressive = [booking for ship in SHIPS for booking in generate_aggressive_bookings(
        ship['id'], aggressive_days, aggressive_rng)]

    return {
        'ships': SHIPS,
        # Keep the two source patterns consecutive in the JSON as well as time.
        'bookings': supplied + aggressive,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--today', type=date.fromisoformat, default=datetime.now(CENTRAL).date(),
                        help='First day of the aggressive period, YYYY-MM-DD (default: today in Central).')
    args = parser.parse_args()
    print(json.dumps(generate_seed(args.today), indent=2))


if __name__ == '__main__':
    main()
