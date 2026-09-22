from django.urls import path
from . import views

urlpatterns = [
    path('ships', views.get_ships),
    path('bookings/unavailable', views.get_unavailable_slots),
    path('bookings', views.booking_handler),
    path('dashboard', views.dashboard),
]
