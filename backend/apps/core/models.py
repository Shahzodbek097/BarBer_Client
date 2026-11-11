"""Umumiy modellar: hududlar (viloyat/tuman) va audit jurnali."""

from django.conf import settings
from django.db import models


class Region(models.Model):
    name = models.CharField("Nomi", max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Viloyat"
        verbose_name_plural = "Viloyatlar"
        ordering = ("name",)

    def __str__(self):
        return self.name


class District(models.Model):
    region = models.ForeignKey(
        Region, on_delete=models.CASCADE, related_name="districts", verbose_name="Viloyat"
    )
    name = models.CharField("Nomi", max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Tuman"
        verbose_name_plural = "Tumanlar"
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(fields=("region", "name"), name="district_unique_in_region"),
        ]

    def __str__(self):
        return f"{self.region} — {self.name}"


class AuditLog(models.Model):
    """Muhim harakatlar jurnali (login/ro'yxat, admin moderatsiya va h.k.).

    Stage 3+ da services qatlami yozadi. Admin'da faqat o'qish.
    """

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        verbose_name="Kim bajardi",
    )
    action = models.CharField("Harakat", max_length=100)
    model_name = models.CharField("Model", max_length=100, blank=True, default="")
    object_id = models.CharField("Obyekt ID", max_length=50, blank=True, default="")
    payload = models.JSONField("Qo'shimcha ma'lumot", default=dict, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Audit yozuvi"
        verbose_name_plural = "Audit yozuvlari"
        ordering = ("-at",)
        indexes = [
            models.Index(fields=("model_name", "object_id")),
            models.Index(fields=("actor", "-at")),
        ]

    def __str__(self):
        return f"{self.action} @ {self.at:%Y-%m-%d %H:%M}"
