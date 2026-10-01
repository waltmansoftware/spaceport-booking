from django.db import models


class Ship(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.name


class Booking(models.Model):
    ship = models.ForeignKey(Ship, on_delete=models.CASCADE, related_name='bookings')
    pilot_name = models.CharField(max_length=255)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    class Meta:
        ordering = ['start_time', 'id']
        indexes = [
            models.Index(fields=['ship', 'start_time', 'id'], name='booking_ship_start_id'),
            models.Index(fields=['start_time', 'id'], name='booking_start_id'),
            models.Index(fields=['ship', 'end_time', 'start_time'], name='booking_ship_end_start'),
        ]
        constraints = [models.CheckConstraint(
            condition=models.Q(end_time__gt=models.F('start_time')),
            name='booking_positive_duration',
        )]
