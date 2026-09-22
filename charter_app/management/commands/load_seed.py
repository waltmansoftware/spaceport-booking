import json
from datetime import datetime
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from charter_app.models import Booking, Ship


class Command(BaseCommand):
    help = 'Replace all ships and bookings with a seed JSON file, atomically.'

    def add_arguments(self, parser):
        parser.add_argument('path', nargs='?', default='seed.json')

    def handle(self, *args, **options):
        try:
            data = json.loads(Path(options['path']).read_text())
            with transaction.atomic():
                Booking.objects.all().delete()
                Ship.objects.all().delete()
                Ship.objects.bulk_create([Ship(id=s['id'], name=s['name']) for s in data['ships']])
                bookings = [Booking(
                    ship_id=b['shipId'], pilot_name=b['pilotName'],
                    start_time=datetime.fromisoformat(b['startTime']),
                    end_time=datetime.fromisoformat(b['endTime']),
                ) for b in data['bookings']]
                Booking.objects.bulk_create(bookings)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise CommandError(f'Could not load seed: {exc}') from exc
        self.stdout.write(self.style.SUCCESS(f'Loaded {len(data["ships"])} ships and {len(bookings)} bookings.'))
