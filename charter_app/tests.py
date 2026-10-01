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
from django.db import close_old_connections, connection
from django.test import TestCase, TransactionTestCase
from django.test.utils import CaptureQueriesContext
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
        self.assertEqual(dashboard.data['count'], 1)
        self.assertEqual(len(dashboard.data['ships'][0]['bookings']), 1)
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
        with self.assertNumQueries(2):
            result = self.client.get('/api/bookings/unavailable', {
                'ship_id': self.ship.pk, 'date': '2026-09-21'})
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
        self.assertEqual(dashboard.data['count'], expected_count)
        self.assertEqual(sum(len(s['bookings']) for s in dashboard.data['ships']), 50)
        for source in [self.seed_data['bookings'][0], self.seed_data['bookings'][3000]]:
            with self.subTest(source=source):
                dashboard = self.client.get('/api/dashboard', {
                    'ship_id': source['shipId'], 'date': source['startTime'][:10]})
                matching = [b for b in dashboard.data['ships'][0]['bookings'] if all(
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


class BookingQueryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ship = Ship.objects.create(name='Nostromo')
        cls.other = Ship.objects.create(name='Serenity')
        start = datetime.fromisoformat('2026-09-21T21:00:00-05:00')
        # Equal timestamps deliberately exercise stable pagination at ties.
        Booking.objects.bulk_create([
            Booking(ship=cls.ship if i % 2 else cls.other, pilot_name=f'Pilot {i}',
                    start_time=start, end_time=start + timedelta(minutes=30))
            for i in range(125)
        ])

    def rows(self, response, endpoint):
        if endpoint == 'dashboard':
            return [b for ship in response.data['ships'] for b in ship['bookings']]
        return response.data['bookings']

    def test_pages_are_bounded_in_sql_and_have_no_n_plus_one_queries(self):
        expected = set(Booking.objects.values_list('id', flat=True))
        for endpoint in ['bookings', 'dashboard']:
            seen = set()
            for page, size in [(1, 50), (2, 50), (3, 25)]:
                with self.subTest(endpoint=endpoint, page=page):
                    with CaptureQueriesContext(connection) as queries:
                        response = self.client.get(f'/api/{endpoint}', {'page': page})
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(len(queries), 2)
                    self.assertIn('COUNT(', queries[0]['sql'])
                    self.assertIn(f'LIMIT {size}', queries[1]['sql'])
                    if page > 1:
                        self.assertIn(f'OFFSET {(page - 1) * 50}', queries[1]['sql'])
                    rows = self.rows(response, endpoint)
                    ids = {b['id'] for b in rows}
                    self.assertEqual(len(rows), size)
                    self.assertFalse(seen & ids)
                    seen.update(ids)
                    self.assertEqual(response.data['count'], 125)
                    self.assertEqual(response.data['totalPages'], 3)
                    self.assertEqual(bool(response.data['next']), page < 3)
                    self.assertEqual(bool(response.data['previous']), page > 1)
            self.assertEqual(seen, expected)

    def test_filters_run_in_sql_and_links_preserve_them(self):
        for endpoint in ['bookings', 'dashboard']:
            with self.subTest(endpoint=endpoint):
                with CaptureQueriesContext(connection) as queries:
                    response = self.client.get(f'/api/{endpoint}', {
                        'ship_id': self.ship.pk, 'date': '2026-09-21', 'page_size': 10})
                self.assertEqual(response.data['count'], 62)
                self.assertEqual(len(self.rows(response, endpoint)), 10)
                self.assertTrue(all(b['shipId'] == self.ship.pk
                                    for b in self.rows(response, endpoint)))
                self.assertIn('WHERE', queries[1]['sql'])
                self.assertIn('"start_time" >=', queries[1]['sql'])
                self.assertIn('"start_time" <', queries[1]['sql'])
                self.assertNotIn('django_datetime_cast_date', queries[1]['sql'])
                self.assertIn(f'ship_id={self.ship.pk}', response.data['next'])
                self.assertIn('date=2026-09-21', response.data['next'])
                self.assertIn('page_size=10', response.data['next'])

    def test_invalid_filters_and_page_limits(self):
        for endpoint in ['bookings', 'dashboard']:
            for params in [
                {'page': 0}, {'page': -1}, {'page': 'bad'},
                {'page_size': 0}, {'page_size': 101}, {'page_size': 'bad'},
                {'ship_id': 0}, {'ship_id': 'bad'},
                {'date': '2026-02-30'}, {'date': 'bad'}, {'date': '9999-12-31'},
            ]:
                with self.subTest(endpoint=endpoint, params=params):
                    self.assertEqual(self.client.get(f'/api/{endpoint}', params).status_code, 400)
            self.assertEqual(self.client.get(f'/api/{endpoint}', {'page': 4}).status_code, 404)
            response = self.client.get(f'/api/{endpoint}', {'page_size': 100})
            self.assertEqual(len(self.rows(response, endpoint)), 100)

    def test_empty_filters_return_empty_page(self):
        for endpoint in ['bookings', 'dashboard']:
            for params in [{'ship_id': 999999}, {'date': '2026-09-22'}]:
                response = self.client.get(f'/api/{endpoint}', params)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data['count'], 0)
                self.assertEqual(self.rows(response, endpoint), [])
                self.assertIsNone(response.data['next'])
                self.assertIsNone(response.data['previous'])

    def test_date_filters_use_central_midnights_across_dst(self):
        from .serializers import CENTRAL
        for day in [date(2026, 3, 8), date(2026, 11, 1)]:
            start = datetime.combine(day, datetime.min.time(), tzinfo=CENTRAL)
            end = datetime.combine(day + timedelta(days=1), datetime.min.time(), tzinfo=CENTRAL)
            Booking.objects.all().delete()
            records = [Booking.objects.create(
                ship=self.ship, pilot_name=str(i), start_time=instant,
                end_time=instant + timedelta(minutes=1),
            ) for i, instant in enumerate([
                start - timedelta(minutes=1), start, end - timedelta(minutes=1), end,
            ])]
            for endpoint in ['bookings', 'dashboard']:
                response = self.client.get(f'/api/{endpoint}', {'date': day.isoformat()})
                self.assertEqual([b['id'] for b in self.rows(response, endpoint)],
                                 [records[1].pk, records[2].pk])

    def test_availability_projects_only_selected_day_and_ship_in_sql(self):
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get('/api/bookings/unavailable', {
                'ship_id': self.ship.pk, 'date': '2026-09-21'})
        self.assertEqual(len(queries), 2)
        sql = queries[1]['sql']
        self.assertIn('WHERE', sql)
        self.assertIn('"end_time" >', sql)
        self.assertIn('"start_time" <', sql)
        projection = sql.split(' FROM ')[0]
        self.assertNotIn('"ship_id"', projection)
        # A daily schedule is complete, even if it exceeds the list page size.
        self.assertEqual(len(response.data['schedule']), 62)
        self.assertEqual(response.data['unavailableSlots'], [{
            'start': '2026-09-21T21:00:00-05:00', 'end': '2026-09-21T22:00:00-05:00',
        }])


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
