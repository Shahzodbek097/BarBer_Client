"""Sartaroshxona modeli.

Geo maydoni (PointField) bosqich 7-da qo'shiladi — hozircha lat/lng
DecimalField sifatida saqlanadi (host'da test tezligi uchun GeoDjango
kutubxonalari talab qilinmaydi).
"""

from django.conf import settings
from django.db import models


class SalonStatus(models.TextChoices):
    PENDING = "pending", "Tasdiqlanmagan"
    APPROVED = "approved", "Tasdiqlangan"
    BLOCKED = "blocked", "Bloklangan"


class Salon(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="salons",
        verbose_name="Egasi",
    )
    name = models.CharField("Nomi", max_length=200)
    slug = models.SlugField("Slug", max_length=220, unique=True)
    region = models.ForeignKey(
        "core.Region", on_delete=models.PROTECT, related_name="salons", verbose_name="Viloyat"
    )
    district = models.ForeignKey(
        "core.District",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="salons",
        verbose_name="Tuman",
    )
    address = models.CharField("Manzil", max_length=255, blank=True, default="")
    phone = models.CharField("Aloqa telefoni", max_length=20, blank=True, default="")
    description = models.TextField("Tavsif", blank=True, default="")
    photos = models.JSONField("Rasmlar (media yo'llari)", default=list, blank=True)
    # Salon umumiy ish vaqti (har sartaroshning o'z jadvali alohida — schedule app)
    work_time_start = models.TimeField("Ish boshlanishi", null=True, blank=True)
    work_time_end = models.TimeField("Ish tugashi", null=True, blank=True)
    # Geo (bosqich 7: 'yaqinimdagi' qidiruv)
    latitude = models.DecimalField("Kenglik", max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(
        "Uzunlik", max_digits=9, decimal_places=6, null=True, blank=True
    )
    # Moderatsiya: admin tasdiqlamaguncha katalogda ko'rinmaydi
    status = models.CharField(
        "Holat",
        max_length=20,
        choices=SalonStatus.choices,
        default=SalonStatus.PENDING,
        db_index=True,
    )
    rating_avg = models.DecimalField("O'rtacha baho", max_digits=3, decimal_places=2, default=0)
    rating_count = models.PositiveIntegerField("Baholar soni", default=0)
    is_deleted = models.BooleanField("O'chirilgan (soft)", default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Sartaroshxona"
        verbose_name_plural = "Sartaroshxonalar"
        ordering = ("name",)
        indexes = [
            models.Index(fields=("region", "status")),
        ]

    def __str__(self):
        return self.name
