"""Xabarnoma moduli (bosqich 4-da emitter orqali yoziladi)."""

from django.conf import settings
from django.db import models


class NotificationType(models.TextChoices):
    BOOKING_NEW = "booking_new", "Yangi navbat so'rovi"
    BOOKING_CONFIRMED = "booking_confirmed", "Navbat tasdiqlandi"
    BOOKING_REJECTED = "booking_rejected", "Navbat rad etildi"
    BOOKING_PROPOSED = "booking_proposed", "Boshqa vaqt taklif qilindi"
    BOOKING_RESCHEDULED = "booking_rescheduled", "Navbat vaqti o'zgartirildi"
    BOOKING_CANCELLED = "booking_cancelled", "Navbat bekor qilindi"
    BOOKING_COMPLETED = "booking_completed", "Xizmat bajarildi"
    BOOKING_REMINDER = "booking_reminder", "Navbat eslatmasi"
    SYSTEM = "system", "Tizim xabari"


class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name="Qabul qiluvchi",
    )
    type = models.CharField("Turi", max_length=30, choices=NotificationType.choices, db_index=True)
    title = models.CharField("Sarlavha", max_length=200)
    body = models.TextField("Matn", blank=True, default="")
    link = models.CharField("Havola", max_length=300, blank=True, default="")
    is_read = models.BooleanField("O'qilgan", default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Xabarnoma"
        verbose_name_plural = "Xabarnomalar"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("recipient", "-created_at")),
            models.Index(fields=("recipient", "is_read")),
        ]

    def __str__(self):
        return f"{self.recipient} — {self.title}"
