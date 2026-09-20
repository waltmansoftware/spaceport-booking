import json
from django.core.management.base import BaseCommand
from datetime import datetime
from your_app.models import Ship, Booking

class Command(BaseCommand):
    help = "Seeds database using data exported from seed.json"

    def handle(self, *args, **options):
        with open('seed.json', 'r') as file:
            data = json.load(file)

        # 1. Clean existing records out
        Booking.objects.all().delete()
        Ship.objects.all().delete()

        # 2. Map existing structures
        ship_map = {}
        for s in data['ships']:
            ship_obj = Ship.objects.create(id=s['id'], name=s['name'])
            ship_map[s['id']] = ship_obj

        # 3. Mass instantiation pipeline
        booking_instances = []
        for b in data['bookings']:
            booking_instances.append(Booking(
                ship=ship_map[b['shipId']],
                pilot_name=b['pilotName'],
                start_time=datetime.fromisoformat(b['startTime']),
                end_time=datetime.fromisoformat(b['endTime'])
            ))
            
        Booking.objects.bulk_create(booking_instances)
        self.stdout.write(self.style.SUCCESS(f'Successfully loaded spaceport data into DB!'))
