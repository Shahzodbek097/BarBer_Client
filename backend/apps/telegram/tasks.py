"""Celery task'lari (bosqich 7): kunlik eslatma."""

from celery import shared_task
from django.utils import timezone

from apps.telegram.services.reminders import send_reminders_for


@shared_task(name="apps.telegram.send_reminders")
def send_reminders_task() -> int:
    """Bugungi tasdiqlangan navbatlarga eslatma (Beat: har kuni 09:00)."""
    return send_reminders_for(timezone.localdate())
