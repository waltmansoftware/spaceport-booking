from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from .models import Ship, Booking
from .serializers import ShipSerializer, BookingSerializer

CENTRAL = ZoneInfo("America/Chicago")
BUFFER = timedelta(minutes=30)

@api_view(['GET'])
def get_ships(request):
    ships = Ship.objects.all()
    serializer = ShipSerializer(ships, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def get_unavailable_slots(request):
    ship_id = request.query_params.get('ship_id')
    date_str = request.query_params.get('date')

    if not ship_id or not date_str:
        return Response({"detail": "Missing parameters ship_id or date"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return Response({"detail": "Invalid date string. Expected YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST)

    # Query matching logs around specific dates to account for offset wrap-arounds
    start_search = datetime.combine(target_date - timedelta(days=1), datetime.min.time(), tzinfo=CENTRAL)
    end_search = datetime.combine(target_date + timedelta(days=1), datetime.max.time(), tzinfo=CENTRAL)

    bookings = Booking.objects.filter(
        ship_id=ship_id,
        end_time__gte=start_search,
        start_time__lte=end_search
    )

    unavailable = []
    for b in bookings:
        b_start_local = b.start_time.astimezone(CENTRAL)
        b_end_local = b.end_time.astimezone(CENTRAL)

        unavailable.append({
            "start": (b_start_local - BUFFER).isoformat(),
            "end": (b_end_local + BUFFER).isoformat(),
            "displayStart": b_start_local.isoformat(),
            "displayEnd": b_end_local.isoformat()
        })

    return Response({
        "date": date_str,
        "shipId": int(ship_id),
        "unavailableSlots": unavailable
    })

@api_view(['GET', 'POST'])
def booking_handler(request):
    if request.method == 'GET':
        # Dashboard dataset delivery pipeline
        ships = Ship.objects.all()
        bookings = Booking.objects.all().order_by('start_time')
        
        return Response({
            "ships": ShipSerializer(ships, many=True).data,
            "bookings": BookingSerializer(bookings, many=True).data
        })

    elif request.method == 'POST':
        serializer = BookingSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "success", "bookingId": serializer.instance.id}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
