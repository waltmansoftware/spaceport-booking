import json
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient
from .models import Booking, Ship


def payload(ship, start='2026-09-21T12:00:00-05:00', end='2026-09-21T13:00:00-05:00'):
    return {'shipId': ship.pk, 'pilotName': 'Ellen Ripley', 'startTime': start, 'endTime': end}


class BookingTests(TestCase):
    def setUp(self):
        self.clock = patch(
            'charter_app.serializers.timezone.now',
            return_value=datetime.fromisoformat('2025-12-31T00:00:00-06:00'),
        )
        self.clock.start()
        self.addCleanup(self.clock.stop)
        self.client = APIClient()
        self.ship = Ship.objects.create(name='Nostromo')

    def post(self, **changes):
        return self.client.post('/api/bookings', {**payload(self.ship), **changes}, format='json')

    def test_valid_booking_and_dashboard(self):
        result = self.post()
        self.assertEqual(result.status_code, 201)
        self.assertEqual(result.data['shipId'], self.ship.pk)
        self.assertEqual(result.data['pilotName'], 'Ellen Ripley')
        with self.assertNumQueries(2):
            dashboard = self.client.get('/api/dashboard')
        self.assertEqual(len(dashboard.data['bookings']), 1)
        self.assertEqual(dashboard.data['ships'][0]['name'], 'Nostromo')
        self.assertEqual(self.client.post('/api/dashboard', {}, format='json').status_code, 405)

    def test_operating_boundaries(self):
        cases = [
            ('2026-09-21T06:00:00-05:00', '2026-09-21T22:00:00-05:00', 201),
            ('2026-09-21T05:59:59-05:00', '2026-09-21T07:00:00-05:00', 400),
            ('2026-09-21T21:00:00-05:00', '2026-09-21T22:00:01-05:00', 400),
            ('2026-09-21T21:00:00-05:00', '2026-09-21T22:59:00-05:00', 400),
            ('2026-09-21T21:00:00-05:00', '2026-09-22T07:00:00-05:00', 400),
            ('2026-09-21T06:00:00-05:00', '2026-09-23T22:00:00-05:00', 400),
            ('2026-09-21T12:00:00-05:00', '2026-09-21T12:00:00-05:00', 400),
            ('2026-09-21T13:00:00-05:00', '2026-09-21T12:00:00-05:00', 400),
        ]
        for start, end, expected in cases:
            with self.subTest(start=start, end=end):
                Booking.objects.all().delete()
                self.assertEqual(self.post(startTime=start, endTime=end).status_code, expected)

    def test_past_bookings_are_rejected(self):
        with patch(
            'charter_app.serializers.timezone.now',
            return_value=datetime.fromisoformat('2026-09-21T10:00:00-05:00'),
        ):
            result = self.post(
                startTime='2026-09-21T09:59:59-05:00',
                endTime='2026-09-21T10:30:00-05:00',
            )
            self.assertEqual(result.status_code, 400)
            self.assertIn('past', str(result.data).lower())
            self.assertEqual(Booking.objects.count(), 0)
            self.assertEqual(self.post(
                startTime='2026-09-21T10:00:00-05:00',
                endTime='2026-09-21T11:00:00-05:00',
            ).status_code, 201)

    def test_overlap_and_refueling_in_both_directions(self):
        self.assertEqual(self.post().status_code, 201)
        cases = [
            ('12:30:00', '13:30:00', 400),
            ('11:00:00', '14:00:00', 400),
            ('12:15:00', '12:45:00', 400),
            ('13:00:00', '14:00:00', 400),
            ('13:29:59', '14:00:00', 400),
            ('10:00:00', '11:30:01', 400),
            ('13:30:00', '14:00:00', 201),
            ('10:00:00', '11:30:00', 201),
        ]
        for start, end, expected in cases:
            with self.subTest(start=start, end=end):
                self.assertEqual(self.post(startTime=f'2026-09-21T{start}-05:00',
                                           endTime=f'2026-09-21T{end}-05:00').status_code, expected)
        other = Ship.objects.create(name='Serenity')
        self.assertEqual(self.post(shipId=other.pk).status_code, 201)

    def test_input_errors_are_400(self):
        for changes in [
            {'shipId': 999999}, {'shipId': 'oops'}, {'pilotName': '   '},
            {'pilotName': 'x' * 256}, {'startTime': 'not a date'},
            {'startTime': '2026-09-21T12:00:00'}, {'endTime': None},
        ]:
            with self.subTest(changes=changes):
                self.assertEqual(self.post(**changes).status_code, 400)
        self.assertEqual(self.client.post('/api/bookings', {}, format='json').status_code, 400)

    def test_central_hours_using_utc_in_winter_summer_and_dst_days(self):
        for day, opening in [
            ('2026-01-15', '12:00'),
            ('2026-07-15', '11:00'),
            ('2026-03-08', '11:00'),
            ('2026-11-01', '12:00'),
        ]:
            # Noon UTC is 06:00 CST, 11:00 UTC is 06:00 CDT.
            with self.subTest(day=day):
                result = self.post(startTime=f'{day}T{opening}:00Z', endTime=f'{day}T14:00:00Z')
                self.assertEqual(result.status_code, 201)
                self.assertEqual(datetime.fromisoformat(result.data['startTime']).hour, 6)
        self.assertEqual(self.post(startTime='2026-01-16T11:59:00Z',
                                   endTime='2026-01-16T14:00:00Z').status_code, 400)

    def test_unavailable_clips_merges_and_excludes_other_dates_and_ships(self):
        for start, end in [('06:00', '07:00'), ('07:30', '08:00'), ('21:00', '22:00')]:
            self.assertEqual(self.post(startTime=f'2026-09-21T{start}:00-05:00',
                                       endTime=f'2026-09-21T{end}:00-05:00').status_code, 201)
        self.post(startTime='2026-09-20T12:00:00-05:00', endTime='2026-09-20T13:00:00-05:00')
        self.post(shipId=Ship.objects.create(name='Other').pk)
        result = self.client.get('/api/bookings/unavailable', {'ship_id': self.ship.pk, 'date': '2026-09-21'})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data['unavailableSlots'], [
            {'start': '2026-09-21T06:00:00-05:00', 'end': '2026-09-21T08:30:00-05:00'},
            {'start': '2026-09-21T21:00:00-05:00', 'end': '2026-09-21T22:00:00-05:00'},
        ])
        self.assertEqual(result.data['schedule'][0]['refueling'], {
            'start': '2026-09-21T07:00:00-05:00', 'end': '2026-09-21T07:30:00-05:00'})
        self.assertIsNone(result.data['schedule'][-1]['refueling'])
        empty = self.client.get('/api/bookings/unavailable', {'ship_id': self.ship.pk, 'date': '2026-09-22'})
        self.assertEqual(empty.data['unavailableSlots'], [])

    def test_unavailable_invalid_parameters(self):
        for params, code in [({}, 400), ({'ship_id': 'abc', 'date': '2026-09-21'}, 400),
                             ({'ship_id': self.ship.pk, 'date': '2026-02-30'}, 400),
                             ({'ship_id': -1, 'date': '2026-09-21'}, 400),
                             ({'ship_id': 999999, 'date': '2026-09-21'}, 404)]:
            with self.subTest(params=params):
                self.assertEqual(self.client.get('/api/bookings/unavailable', params).status_code, code)

    def test_seed_replacement_and_rollback(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'seed.json'
            seed = {'ships': [{'id': 7, 'name': 'Rocinante'}], 'bookings': [{**payload(self.ship), 'shipId': 7}]}
            path.write_text(json.dumps(seed))
            for _ in range(2):
                call_command('load_seed', str(path), stdout=StringIO())
                self.assertEqual(Ship.objects.count(), 1)
                self.assertEqual(Booking.objects.count(), 1)
            seed['bookings'][0]['startTime'] = 'broken'
            path.write_text(json.dumps(seed))
            with self.assertRaises(CommandError):
                call_command('load_seed', str(path), stdout=StringIO())
            self.assertEqual(Ship.objects.get().name, 'Rocinante')
            self.assertEqual(Booking.objects.count(), 1)


class ImportedSeedTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from seed import generate_seed
        cls.seed_data = generate_seed(date(2026, 9, 30), random_seed=42)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'seed.json'
            path.write_text(json.dumps(cls.seed_data))
            call_command('load_seed', str(path), stdout=StringIO())

    def setUp(self):
        self.clock = patch(
            'charter_app.serializers.timezone.now',
            return_value=datetime.fromisoformat('2026-09-30T00:00:00-05:00'),
        )
        self.clock.start()
        self.addCleanup(self.clock.stop)
        self.client = APIClient()

    def test_imported_history_and_future_are_visible_and_block_conflicts(self):
        dashboard = self.client.get('/api/dashboard')
        expected_count = len(self.seed_data['bookings'])
        self.assertEqual(len(dashboard.data['bookings']), expected_count)
        for source in [self.seed_data['bookings'][0], self.seed_data['bookings'][3000]]:
            with self.subTest(source=source):
                matching = [b for b in dashboard.data['bookings'] if all(
                    b[key] == value for key, value in source.items())]
                self.assertEqual(len(matching), 1)
                slots = self.client.get('/api/bookings/unavailable', {
                    'ship_id': source['shipId'], 'date': source['startTime'][:10]})
                entry = next(b for b in slots.data['schedule'] if b['bookingId'] == matching[0]['id'])
                self.assertEqual(entry['start'], source['startTime'])
                self.assertEqual(entry['pilotName'], source['pilotName'])
                result = self.client.post('/api/bookings', source, format='json')
                self.assertEqual(result.status_code, 400)
                self.assertEqual(Booking.objects.count(), expected_count)

    def test_insert_before_and_after_imported_flight_at_exact_buffer(self):
        future = self.seed_data['bookings'][3000:]
        counts = {}
        for booking in future:
            key = (booking['shipId'], booking['startTime'][:10])
            counts[key] = counts.get(key, 0) + 1
        source = next(booking for booking in future if counts[
            (booking['shipId'], booking['startTime'][:10])
        ] == 1 and 8 <= datetime.fromisoformat(booking['startTime']).hour <= 18)
        source_start = datetime.fromisoformat(source['startTime'])
        source_end = datetime.fromisoformat(source['endTime'])
        before = {
            **source,
            'startTime': (source_start - timedelta(hours=1, minutes=30)).isoformat(),
            'endTime': (source_start - timedelta(minutes=30)).isoformat(),
        }
        result = self.client.post('/api/bookings', before, format='json')
        self.assertEqual(result.status_code, 201)
        slots = self.client.get('/api/bookings/unavailable', {
            'ship_id': source['shipId'], 'date': source['startTime'][:10]})
        self.assertEqual(slots.data['unavailableSlots'][0]['start'], before['startTime'])
        self.assertIn(result.data['id'], [b['bookingId'] for b in slots.data['schedule']])
        after = {
            **source,
            'startTime': (source_end + timedelta(minutes=30)).isoformat(),
            'endTime': (source_end + timedelta(hours=1, minutes=30)).isoformat(),
        }
        self.assertEqual(self.client.post('/api/bookings', after, format='json').status_code, 201)
        self.assertEqual(Booking.objects.count(), len(self.seed_data['bookings']) + 2)


class ConcurrentBookingTests(TransactionTestCase):
    def setUp(self):
        self.clock = patch(
            'charter_app.serializers.timezone.now',
            return_value=datetime.fromisoformat('2025-12-31T00:00:00-06:00'),
        )
        self.clock.start()
        self.addCleanup(self.clock.stop)

    def test_simultaneous_requests_cannot_double_book(self):
        ship = Ship.objects.create(name='Rocinante')
        data = payload(ship)
        barrier = threading.Barrier(2)

        def submit():
            close_old_connections()
            try:
                barrier.wait(timeout=5)
                return APIClient().post('/api/bookings', data, format='json').status_code
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            statuses = list(executor.map(lambda _: submit(), range(2)))
        self.assertEqual(sorted(statuses), [201, 400])
        self.assertEqual(Booking.objects.count(), 1)
