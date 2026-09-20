from django.db import models

class Ship(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class Booking(models.Model):
    ship = models.ForeignKey(Ship, on_delete=models.CASCADE, related_name='bookings')
    pilot_name = models.CharField(max_length=255)
    start_time = models.DateTimeField(db_index=True)
    end_time = models.DateTimeField(db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['ship', 'start_time', 'end_time']),
        ]
