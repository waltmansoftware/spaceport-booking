from datetime import date
from django.db import OperationalError, transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Booking, Ship
from .queries import booking_page
from .serializers import BUFFER, CENTRAL, BookingSerializer, ShipSerializer, operating_window


@api_view(['GET'])
def get_ships(request):
    return Response(ShipSerializer(Ship.objects.all(), many=True).data)


@api_view(['GET'])
def get_unavailable_slots(request):
    try:
        ship_id = int(request.query_params.get('ship_id', ''))
        date_str = request.query_params.get('date', '')
        day = date.fromisoformat(date_str)
        if day.isoformat() != date_str or ship_id <= 0:
            raise ValueError
    except (ValueError, TypeError):
        raise serializers.ValidationError('Provide a positive ship_id and a date in YYYY-MM-DD format.')
    ship = get_object_or_404(Ship.objects.only('id'), pk=ship_id)
    opening, closing = operating_window(day)
    bookings = Booking.objects.filter(
        ship_id=ship_id, end_time__gt=opening - BUFFER, start_time__lt=closing,
    ).values('id', 'pilot_name', 'start_time', 'end_time').order_by('start_time', 'id')
    merged = []
    schedule = []
    for booking in bookings:
        flight_start = booking['start_time'].astimezone(CENTRAL)
        flight_end = booking['end_time'].astimezone(CENTRAL)
        # Occupancy starts at departure; only the trailing refueling blocks time.
        start = max(opening, flight_start)
        end = min(closing, flight_end + BUFFER)
        refuel_start = max(opening, flight_end)
        schedule.append({
            'bookingId': booking['id'], 'pilotName': booking['pilot_name'],
            'start': flight_start.isoformat(), 'end': flight_end.isoformat(),
            'refueling': {'start': refuel_start.isoformat(), 'end': end.isoformat()}
            if refuel_start < end else None,
        })
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return Response({
        'date': date_str, 'shipId': ship.id,
        'opensAt': opening.isoformat(), 'closesAt': closing.isoformat(),
        'unavailableSlots': [{'start': start.isoformat(), 'end': end.isoformat()} for start, end in merged],
        'schedule': schedule,
    })


@api_view(['GET', 'POST'])
def booking_handler(request):
    if request.method == 'GET':
        paginator, bookings = booking_page(request)
        return Response({
            **paginator.metadata(),
            'bookings': BookingSerializer(bookings, many=True).data,
        })
    try:
        # SQLite serializes writers before the conflict read, including across processes.
        with transaction.atomic():
            serializer = BookingSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
    except OperationalError as exc:
        if 'locked' not in str(exc).lower():
            raise
        return Response({'detail': 'The database is busy. Please retry.'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def dashboard(request):
    paginator, bookings = booking_page(request, with_ship=True)
    # Group only the SQL-limited page; related ships arrive in the same query.
    ships = {}
    for booking, data in zip(bookings, BookingSerializer(bookings, many=True).data):
        group = ships.setdefault(booking.ship_id, {
            'id': booking.ship_id, 'name': booking.ship.name, 'bookings': [],
        })
        group['bookings'].append(data)
    return Response({
        **paginator.metadata(),
        'ships': list(ships.values()),
    })
