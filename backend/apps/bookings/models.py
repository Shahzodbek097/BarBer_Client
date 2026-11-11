"""Navbat (Appointment) va uning tarixi.

Kritik constraint — `appointment_active_slot_unique`: bir sartarosh,
bir sana, bir vaqtga faqat bitta AKTIV navbat (CANCELLED va REJECTED
istisno). Bu ikkilangan bandlovning bazaviy himoyasi; qo'shimcha
transaksiya darajasidagi himoya bosqich 4-dagi service qatlamida.
"""

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q


class AppointmentStatus(models.TextChoices):
    PENDING = "pending", "Kutilmoqda"
    CONFIRMED = "confirmed", "Tasdiqlangan"
    COMPLETED = "completed", "Bajarildi"
    REJECTED = "rejected", "Rad etildi"
    CANCELLED = "cancelled", "Bekor qilindi"
    NO_SHOW = "no_show", "Mijoz kelmadi"


class AppointmentSource(models.TextChoices):
    ONLINE = "online", "Onlayn"
    MANUAL = "manual", "Qo'lda (sartarosh)"
    WALK_IN = "walk_in", "Orxonadagi mijoz"


class Appointment(models.Model):
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="appointments",
        verbose_name="Mijoz",
    )
    barber = models.ForeignKey(
        "barbers.BarberProfile",
        on_delete=models.PROTECT,
        related_name="appointments",
        verbose_name="Sartarosh",
    )
    salon = models.ForeignKey(
        "salons.Salon",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appointments",
        verbose_name="Sartaroshxona",
    )
    service = models.ForeignKey(
        "services.Service",
        on_delete=models.PROTECT,
        related_name="appointments",
        verbose_name="Xizmat",
    )
    date = models.DateField("Sana", db_index=True)
    start_time = models.TimeField("Boshlanish vaqti")
    end_time = models.TimeField("Tugash vaqti")
    status = models.CharField(
        "Holat",
        max_length=20,
        choices=AppointmentStatus.choices,
        default=AppointmentStatus.PENDING,
        db_index=True,
    )
    source = models.CharField(
        "Manba",
        max_length=20,
        choices=AppointmentSource.choices,
        default=AppointmentSource.ONLINE,
    )
    # Xizmat narxi bandlov paytidagi qiymat bilan muzlatiladi
    price = models.DecimalField("Narx (UZS)", max_digits=12, decimal_places=2, default=Decimal("0"))
    client_note = models.CharField("Mijoz izohi", max_length=500, blank=True, default="")
    barber_reply = models.CharField("Sartarosh javobi", max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Navbat"
        verbose_name_plural = "Navbatlar"
        ordering = ("date", "start_time")
        indexes = [
            models.Index(fields=("barber", "date")),
            models.Index(fields=("client", "-created_at")),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("barber", "date", "start_time"),
                condition=~Q(
                    status__in=[
                        AppointmentStatus.CANCELLED,
                        AppointmentStatus.REJECTED,
                    ]
                ),
                name="appointment_active_slot_unique",
            ),
        ]

    def __str__(self):
        return f"{self.client} → {self.barber} ({self.date} {self.start_time})"


class AppointmentHistory(models.Model):
    """Har holat o'tishining yozuvi (kuzatuv va tahlil uchun)."""

    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name="history",
        verbose_name="Navbat",
    )
    old_status = models.CharField(  # noqa: DJ001
        "Eski holat", max_length=20, choices=AppointmentStatus.choices, null=True, blank=True
    )
    new_status = models.CharField("Yangi holat", max_length=20, choices=AppointmentStatus.choices)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="Kim o'zgartirdi",
    )
    comment = models.CharField("Izoh", max_length=300, blank=True, default="")
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Navbat tarixi"
        verbose_name_plural = "Navbat tarixlari"
        ordering = ("-at",)
        indexes = [
            models.Index(fields=("appointment", "-at")),
        ]

    def __str__(self):
        return f"#{self.appointment_id}: {self.old_status or '-'} → {self.new_status}"
