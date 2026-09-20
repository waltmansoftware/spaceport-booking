from rest_framework import serializers
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from django.utils.dateparse import parse_datetime
from .models import Ship, Booking

CENTRAL = ZoneInfo("America/Chicago")
BUFFER = timedelta(minutes=30)

class ShipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ship
        fields = ['id', 'name']

class BookingSerializer(serializers.ModelSerializer):
    shipId = serializers.IntegerField(source='ship.id')
    pilotName = serializers.CharField(source='pilot_name')
    startTime = serializers.CharField(source='start_time')
    endTime = serializers.CharField(source='end_time')

    class Meta:
        model = Booking
        fields = ['id', 'shipId', 'pilotName', 'startTime', 'endTime']

    def validate(self, data):
        ship_id = data['ship']['id']
        pilot_name = data['pilot_name']
        
        # 1. Standardize parsing and assign appropriate Timezone awareness
        try:
            start_dt = datetime.fromisoformat(data['start_time']).astimezone(CENTRAL)
            end_dt = datetime.fromisoformat(data['end_time']).astimezone(CENTRAL)
        except (ValueError, TypeError):
            raise serializers.ValidationError("Invalid ISO-8601 datetime strings format.")

        if start_dt >= end_dt:
            raise serializers.ValidationError("The flight's starting window must precede its ending time.")

        # 2. Enforce operating hours constraint
        if not (6 <= start_dt.hour < 22) or not (6 <= end_dt.hour <= 22 or (end_dt.hour == 22 and end_dt.minute == 0)):
            raise serializers.ValidationError("Launch allocations must fall purely within operating hours (06:00 to 22:00 Central).")

        # 3. Apply the 30-minute buffer window rule onto interval collisions
        check_start = start_dt - BUFFER
        check_end = end_dt + BUFFER

        # DB lookups work seamlessly across timezones as Django converts inputs to UTC
        conflicts = Booking.objects.filter(
            ship_id=ship_id,
            end_time__gt=check_start,
            start_time__lt=check_end
        )

        if conflicts.exists():
            raise serializers.ValidationError("Time slot conflict detected. Consecutive charters require an open 30-minute refueling window.")

        # Reformat data safely mapping back to database fields
        return {
            'ship_id': ship_id,
            'pilot_name': pilot_name,
            'start_time': start_dt,
            'end_time': end_dt
        }
