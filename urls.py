from django.urls import path
from . import views

urlpatterns = [
    path('api/ships', views.get_ships, name='ships'),
    path('api/bookings/unavailable', views.get_unavailable_slots, name='unavailable'),
    path('api/bookings', views.booking_handler, name='bookings'),
    path('api/dashboard', views.booking_handler, name='dashboard'), 
]
