"""Telegram chat bog'lash modellari (bosqich 7).

Chain: veb-kabinetda kod olinadi → foydalanuvchi botga `/start KOD`
yuboradi → `TelegramChat` bog'lanadi → eslatma/holat xabarlari shu
chatga ketadi (bo'lmasa SMS fallback — `services/reminders.py`).
"""

from django.conf import settings
from django.db import models
from django.utils import timezone


class TelegramChat(models.Model):
    """Foydalanuvchi ↔ Telegram chat bog'lanishi (1:1 — qayta ulash yangilaydi)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="telegram_chat",
        verbose_name="Foydalanuvchi",
    )
    chat_id = models.BigIntegerField("Chat ID", unique=True)
    username = models.CharField("Telegram username", max_length=100, blank=True, default="")
    is_active = models.BooleanField("Faol", default=True)
    linked_at = models.DateTimeField("Ulangan vaqt", auto_now_add=True)

    class Meta:
        verbose_name = "Telegram chat"
        verbose_name_plural = "Telegram chatlar"

    def __str__(self):
        return f"{self.user} → {self.chat_id}"


class LinkCode(models.Model):
    """Bir martalik ulanish kodi (umri `TELEGRAM_LINK_TTL` sekund)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="telegram_link_codes",
        verbose_name="Foydalanuvchi",
    )
    code = models.CharField("Kod", max_length=8, unique=True)
    expires_at = models.DateTimeField("Amal qilish muddati")
    used_at = models.DateTimeField("Ishlatilgan vaqt", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Ulanish kodi"
        verbose_name_plural = "Ulanish kodlari"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.user} — {self.code}"

    @property
    def is_usable(self) -> bool:
        return self.used_at is None and self.expires_at > timezone.now()
