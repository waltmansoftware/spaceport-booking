"""Validated, SQL-filtered booking pages shared by both list endpoints."""
from datetime import datetime, time, timedelta

from rest_framework import serializers
from rest_framework.pagination import PageNumberPagination

from .models import Booking
from .serializers import CENTRAL


class BookingFilters(serializers.Serializer):
    ship_id = serializers.IntegerField(min_value=1, required=False)
    date = serializers.DateField(input_formats=['%Y-%m-%d'], required=False)
    page = serializers.IntegerField(min_value=1, default=1)
    page_size = serializers.IntegerField(min_value=1, max_value=100, default=50)


class BookingPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 100

    def metadata(self):
        return {
            'count': self.page.paginator.count,
            'page': self.page.number,
            'pageSize': self.get_page_size(self.request),
            'totalPages': self.page.paginator.num_pages,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
        }


def booking_page(request, *, with_ship=False):
    filters = BookingFilters(data=request.query_params)
    filters.is_valid(raise_exception=True)
    params = filters.validated_data
    bookings = Booking.objects.order_by('start_time', 'id')
    if 'ship_id' in params:
        bookings = bookings.filter(ship_id=params['ship_id'])
    if 'date' in params:
        # Raw timestamp bounds preserve index use and respect 23/25-hour DST days.
        day = params['date']
        if day.year == 9999 and day.month == 12 and day.day == 31:
            raise serializers.ValidationError({'date': 'Date is outside the supported range.'})
        start = datetime.combine(day, time.min, tzinfo=CENTRAL)
        end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=CENTRAL)
        bookings = bookings.filter(start_time__gte=start, start_time__lt=end)
    if with_ship:
        bookings = bookings.select_related('ship')
    paginator = BookingPagination()
    return paginator, paginator.paginate_queryset(bookings, request)
