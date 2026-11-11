"""Sartarosh profili va sevimlilar."""

from django.conf import settings
from django.db import models


class BarberStatus(models.TextChoices):
    PENDING = "pending", "Tasdiqlanmagan"
    APPROVED = "approved", "Tasdiqlangan"
    BLOCKED = "blocked", "Bloklangan"


class BarberProfile(models.Model):
    """Sartarosh: har biri alohida shaxsiy kabinet (TZ US-3, US-5).

    salon = NULL bo'lsa — mustaqil (saloonsiz) sartarosh.
    is_active_now — Faol/Nofaol tugmasi (kun boshida ochish, oxirida yopish).
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="barber_profile",
        verbose_name="Foydalanuvchi",
    )
    salon = models.ForeignKey(
        "salons.Salon",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="barbers",
        verbose_name="Sartaroshxona",
    )
    experience_years = models.PositiveSmallIntegerField("Tajriba (yil)", default=0)
    bio = models.TextField("O'zi haqida", blank=True, default="")
    specialties = models.ManyToManyField(
        "services.ServiceCategory",
        blank=True,
        related_name="barbers",
        verbose_name="Mutaxassisliklar",
    )
    portfolio_images = models.JSONField("Portfolio rasmlari", default=list, blank=True)
    status = models.CharField(
        "Holat",
        max_length=20,
        choices=BarberStatus.choices,
        default=BarberStatus.PENDING,
        db_index=True,
    )
    is_active_now = models.BooleanField("Hozir faol", default=False, db_index=True)
    rating_avg = models.DecimalField("O'rtacha baho", max_digits=3, decimal_places=2, default=0)
    rating_count = models.PositiveIntegerField("Baholar soni", default=0)
    is_deleted = models.BooleanField("O'chirilgan (soft)", default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Sartarosh"
        verbose_name_plural = "Sartaroshlar"
        ordering = ("-rating_avg",)
        indexes = [
            models.Index(fields=("status", "is_active_now")),
        ]

    def __str__(self):
        return self.user.full_name or self.user.phone


class Favorite(models.Model):
    """Mijozning sevimli sartaroshlari (tezkor qayta yozilish)."""

    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorites",
        verbose_name="Mijoz",
    )
    barber = models.ForeignKey(
        BarberProfile,
        on_delete=models.CASCADE,
        related_name="favorited_by",
        verbose_name="Sartarosh",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Sevimli"
        verbose_name_plural = "Sevimlilar"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("client", "barber"), name="favorite_unique_client_barber"
            ),
        ]

    def __str__(self):
        return f"{self.client} → {self.barber}"
