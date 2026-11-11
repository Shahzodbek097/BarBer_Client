"""Xizmat kategoriyalari va xizmatlar (narx, davomiylik).

Xizmat egasi yoki sartarosh (owner_type=barber), yoki sartaroshxona
(owner_type=salon) — ikkalasi bir vaqtda bo'lishi mumkin emas
(service_owner_xor DB cheklovi).
"""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class ServiceCategory(models.Model):
    """Umumiy katalog kategoriyalari: Soch, Soqol, Bosh yuvish, Prisochka..."""

    name = models.CharField("Nomi", max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    order = models.PositiveSmallIntegerField("Tartibi", default=0)

    class Meta:
        verbose_name = "Xizmat kategoriyasi"
        verbose_name_plural = "Xizmat kategoriyalari"
        ordering = ("order", "name")

    def __str__(self):
        return self.name


class ServiceOwner(models.TextChoices):
    BARBER = "barber", "Sartarosh"
    SALON = "salon", "Sartaroshxona"


class Service(models.Model):
    owner_type = models.CharField(
        "Egasi turi", max_length=10, choices=ServiceOwner.choices, db_index=True
    )
    barber = models.ForeignKey(
        "barbers.BarberProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="services",
        verbose_name="Sartarosh",
    )
    salon = models.ForeignKey(
        "salons.Salon",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="services",
        verbose_name="Sartaroshxona",
    )
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.PROTECT,
        related_name="services",
        verbose_name="Kategoriya",
    )
    name = models.CharField("Nomi", max_length=200)
    duration_min = models.PositiveSmallIntegerField(
        "Davomiylik (daqiqa)", validators=[MinValueValidator(1)]
    )
    price = models.DecimalField(
        "Narx (UZS)",
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    description = models.TextField("Tavsif", blank=True, default="")
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Xizmat"
        verbose_name_plural = "Xizmatlar"
        ordering = ("name",)
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(owner_type=ServiceOwner.BARBER, barber__isnull=False, salon__isnull=True)
                    | Q(owner_type=ServiceOwner.SALON, salon__isnull=False, barber__isnull=True)
                ),
                name="service_owner_xor",
            ),
            models.CheckConstraint(
                condition=Q(duration_min__gt=0), name="service_duration_positive"
            ),
            models.CheckConstraint(condition=Q(price__gte=0), name="service_price_non_negative"),
        ]

    def __str__(self):
        return f"{self.name} ({self.duration_min} min)"
