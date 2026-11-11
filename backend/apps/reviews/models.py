"""Baholar va izohlar.

Faqat COMPLETED navbatga yoziladi (shart bosqich 4-dagi service qatlamida),
har navbat = 1 sharh (OneToOne). Sartarosh rating'ining qayta hisoblanishi
ham bosqich 4-da.
"""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Review(models.Model):
    appointment = models.OneToOneField(
        "bookings.Appointment",
        on_delete=models.CASCADE,
        related_name="review",
        verbose_name="Navbat",
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reviews",
        verbose_name="Mijoz",
    )
    barber = models.ForeignKey(
        "barbers.BarberProfile",
        on_delete=models.PROTECT,
        related_name="reviews",
        verbose_name="Sartarosh",
    )
    rating = models.PositiveSmallIntegerField(
        "Baho (1-5)", validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField("Izoh", blank=True, default="")
    barber_reply = models.TextField("Sartarosh javobi", blank=True, default="")
    is_visible = models.BooleanField("Ko'rinadi", default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Baho"
        verbose_name_plural = "Baholar"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("barber", "rating")),
        ]

    def __str__(self):
        return f"{self.barber}: {self.rating}/5"
