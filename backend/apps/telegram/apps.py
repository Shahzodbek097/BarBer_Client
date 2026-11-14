"""Telegram ilovasi konfiguratsiyasi (bosqich 7)."""

from django.apps import AppConfig


class TelegramConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.telegram"
    verbose_name = "Telegram (chat bog'lash, eslatmalar)"

    def ready(self) -> None:
        # Notification → Telegram ko'prik (import yo'nalishi: telegram → notifications)
        from apps.telegram import receivers  # noqa: F401,PLC0415
