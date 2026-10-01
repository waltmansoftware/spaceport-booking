"""Generate randomized historical data plus one lightly booked future week.

    python seed.py > seed.json
    python seed.py --today 2026-10-01 --random-seed 42 > seed.json

By default, each invocation uses fresh randomness. Supplying --random-seed makes
the output reproducible for tests and troubleshooting. This command only emits
JSON; importing it remains a separate operation.
"""
import argparse
import json
import random
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from seed_original import PILOTS, SHIPS

CENTRAL = ZoneInfo('America/Chicago')
HISTORY_DAYS = 365
HISTORICAL_BOOKINGS_PER_SHIP = 600
FUTURE_DAYS = 7
MAX_FUTURE_BOOKINGS_PER_SHIP_DAY = 2
REFUEL_BUFFER = timedelta(minutes=30)


def generate_historical_bookings(ship_id, period_start, rng):
    """Generate the supplied timing pattern over the previous year."""
    bookings = []
    cursor = None
    day = period_start
    period_end = period_start + timedelta(days=HISTORY_DAYS)

    while len(bookings) < HISTORICAL_BOOKINGS_PER_SHIP and day < period_end:
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

    if len(bookings) != HISTORICAL_BOOKINGS_PER_SHIP:
        raise RuntimeError('Historical pattern did not reach its booking quota.')
    return bookings


def generate_future_bookings(ship_id, today, rng):
    """Generate one or two well-spaced flights on each of the next seven days."""
    bookings = []
    candidate_hours = [7, 10, 13, 16, 19]
    for offset in range(1, FUTURE_DAYS + 1):
        day = today + timedelta(days=offset)
        count = rng.randint(1, MAX_FUTURE_BOOKINGS_PER_SHIP_DAY)
        for hour in sorted(rng.sample(candidate_hours, count)):
            start = datetime.combine(day, time(hour), CENTRAL)
            end = start + timedelta(minutes=rng.choice([60, 90, 120]))
            bookings.append({
                'shipId': ship_id,
                'pilotName': rng.choice(PILOTS),
                'startTime': start.isoformat(),
                'endTime': end.isoformat(),
            })
    return bookings


def generate_seed(today, random_seed=None):
    rng = random.Random(random_seed)
    historical_start = today - timedelta(days=HISTORY_DAYS)
    historical = [
        booking
        for ship in SHIPS
        for booking in generate_historical_bookings(ship['id'], historical_start, rng)
    ]
    future = [
        booking
        for ship in SHIPS
        for booking in generate_future_bookings(ship['id'], today, rng)
    ]
    return {'ships': SHIPS, 'bookings': historical + future}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--today',
        type=date.fromisoformat,
        default=datetime.now(CENTRAL).date(),
        help='Current Central date, YYYY-MM-DD (default: today).',
    )
    parser.add_argument(
        '--random-seed',
        type=int,
        help='Optional deterministic random seed; omitted means fresh data each run.',
    )
    args = parser.parse_args()
    print(json.dumps(generate_seed(args.today, args.random_seed), indent=2))


if __name__ == '__main__':
    main()
