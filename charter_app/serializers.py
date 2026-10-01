from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from rest_framework import serializers
from .models import Booking, Ship

CENTRAL = ZoneInfo('America/Chicago')
BUFFER = timedelta(minutes=30)


def operating_window(day):
    return (datetime.combine(day, time(6), tzinfo=CENTRAL),
            datetime.combine(day, time(22), tzinfo=CENTRAL))


class OffsetDateTimeField(serializers.DateTimeField):
    def to_internal_value(self, value):
        try:
            parsed = parse_datetime(value) if isinstance(value, str) else None
        except (ValueError, TypeError):
            parsed = None
        if parsed is None or parsed.utcoffset() is None:
            raise serializers.ValidationError('Use an ISO-8601 timestamp with a timezone offset.')
        return super().to_internal_value(value)


class ShipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ship
        fields = ['id', 'name']


class BookingSerializer(serializers.ModelSerializer):
    shipId = serializers.PrimaryKeyRelatedField(source='ship', queryset=Ship.objects.all())
    pilotName = serializers.CharField(source='pilot_name', max_length=255)
    startTime = OffsetDateTimeField(source='start_time')
    endTime = OffsetDateTimeField(source='end_time')

    class Meta:
        model = Booking
        fields = ['id', 'shipId', 'pilotName', 'startTime', 'endTime']
        read_only_fields = ['id']

    def validate(self, data):
        start = data['start_time'].astimezone(CENTRAL)
        end = data['end_time'].astimezone(CENTRAL)
        if start < timezone.now():
            raise serializers.ValidationError('Bookings cannot start in the past.')
        opening, closing = operating_window(start.date())
        if not opening <= start < end <= closing:
            raise serializers.ValidationError(
                'Book a positive duration entirely between 06:00 and 22:00 on one Central Time date.')
        # Compare each flight's [start, end + 30 minutes) occupancy. The end
        # comparison below is equivalent to start < existing.end + BUFFER;
        # it checks the previous flight, while start_time checks the next one.
        # Caller must hold an IMMEDIATE transaction through validation AND save.
        if Booking.objects.filter(
            ship=data['ship'], end_time__gt=start - BUFFER,
            start_time__lt=end + BUFFER,
        ).exists():
            raise serializers.ValidationError(
                'This slot is unavailable. Leave at least 30 minutes between bookings.')
        return data
