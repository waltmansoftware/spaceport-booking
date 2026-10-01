"""Measure seed occupancy during Central operating hours; never modifies data.

python analysis/seed_utilization.py --start 2025-09-30 --end 2026-09-30 seed.json
End date is exclusive. Refueling is 30 minutes AFTER each flight only.
"""
import argparse
import json
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

CENTRAL = ZoneInfo('America/Chicago')


def union_minutes(intervals):
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(end, merged[-1][1])
        else:
            merged.append([start, end])
    return sum((end.astimezone(timezone.utc) - start.astimezone(timezone.utc)).total_seconds() / 60
               for start, end in merged)


def analyze(data, start_date, end_date):
    if end_date <= start_date:
        raise ValueError('End date must follow start date.')
    ship_ids = {ship['id'] for ship in data['ships']}
    if not ship_ids:
        raise ValueError('At least one ship is required.')
    flights, occupied = defaultdict(list), defaultdict(list)
    included = before = after = 0
    for booking in data['bookings']:
        ship_id = booking['shipId']
        if ship_id not in ship_ids:
            raise ValueError('Unknown ship in booking.')
        start = datetime.fromisoformat(booking['startTime'])
        end = datetime.fromisoformat(booking['endTime'])
        if start.utcoffset() is None or end.utcoffset() is None or end <= start:
            raise ValueError('Bookings require aware timestamps and positive duration.')
        start, end = start.astimezone(CENTRAL), end.astimezone(CENTRAL)
        before += start.date() < start_date
        after += start.date() >= end_date
        included += start_date <= start.date() < end_date
        refuel_end = end + timedelta(minutes=30)
        day = max(start.date(), start_date)
        while day < end_date and day <= refuel_end.date():
            opening = datetime.combine(day, time(6), CENTRAL)
            closing = datetime.combine(day, time(22), CENTRAL)
            left, flight_right = max(start, opening), min(end, closing)
            busy_right = min(refuel_end, closing)
            key = (ship_id, day)
            if left < flight_right:
                flights[key].append((left, flight_right))
            if left < busy_right:
                occupied[key].append((left, busy_right))
            day += timedelta(days=1)
    days = (end_date - start_date).days
    capacity = days * len(ship_ids) * 16 * 60
    flight_minutes = sum(union_minutes(v) for v in flights.values())
    busy_minutes = sum(union_minutes(v) for v in occupied.values())
    active_capacity = len(occupied) * 16 * 60
    return {
        'days': days, 'ships': len(ship_ids), 'file_bookings': len(data['bookings']),
        'bookings_in_window': included, 'bookings_before_window': before,
        'bookings_on_or_after_end': after,
        'capacity_hours': capacity / 60, 'flight_hours': flight_minutes / 60,
        'refueling_hours_within_open_hours': (busy_minutes - flight_minutes) / 60,
        'busy_hours': busy_minutes / 60, 'available_hours': (capacity - busy_minutes) / 60,
        'flight_percent': flight_minutes / capacity * 100,
        'busy_percent': busy_minutes / capacity * 100,
        'available_percent': (capacity - busy_minutes) / capacity * 100,
        'active_ship_days': len(occupied), 'total_ship_days': days * len(ship_ids),
        'busy_percent_on_active_ship_days': busy_minutes / active_capacity * 100 if active_capacity else 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start', required=True, type=date.fromisoformat)
    parser.add_argument('--end', required=True, type=date.fromisoformat)
    parser.add_argument('files', nargs='+', type=Path)
    args = parser.parse_args()
    result = {str(path): analyze(json.loads(path.read_text()), args.start, args.end) for path in args.files}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
