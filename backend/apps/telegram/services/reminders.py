"""Kunlik eslatmalar (gate: navbat → tasdiq → eslatma zanjiri).

Har bir tasdiqlangan navbat uchun:
- chat bog'langan → Telegram xabar (Notification emitteri orqali —
  post_save ko'prik ham xuddi shu yerdan yuboradi);
- chat YO'Q → SMS fallback (`accounts/services/sms.py` adapteri).
Ikkilanish: `Appointment.reminded_at` — bir navbatga bitta eslatma.
"""

import logging
from datetime import date

from django.utils import timezone

from apps.accounts.services.sms import get_sms_client
from apps.bookings.models import Appointment, AppointmentStatus
from apps.notifications.models import NotificationType
from apps.notifications.services.emitter import notify
from apps.telegram.models import TelegramChat

logger = logging.getLogger(__name__)


def _slot_text(appt: Appointment) -> str:
    return f"{appt.date:%d.%m} {appt.start_time:%H:%M}"


def _reminder_body(appt: Appointment) -> str:
    return (
        f"Bugun {_slot_text(appt)} — {appt.service.name}, sartarosh: {appt.barber.user.full_name}."
    )


def _sms_text(appt: Appointment) -> str:
    return f"BarBer: bugun {_slot_text(appt)} navbatingiz bor. {_reminder_body(appt)}"


def send_reminders_for(day: date) -> int:
    """Berilgan kun tasdiqlangan navbatlariga eslatma. Qaytaradi: yuborilganlar soni."""
    appointments = (
        Appointment.objects.filter(
            date=day,
            status=AppointmentStatus.CONFIRMED,
            reminded_at__isnull=True,
        )
        .select_related("client", "barber__user", "service")
        .order_by("start_time")
    )
    sent = 0
    for appt in appointments:
        body = _reminder_body(appt)
        try:
            has_chat = TelegramChat.objects.filter(user=appt.client, is_active=True).exists()
            if not has_chat:
                # SMS fallback — chat bog'lanmagan mijozga
                get_sms_client().send(appt.client.phone, _sms_text(appt))
        except Exception:  # noqa: BLE001 — eslatma tsiklni buzmaydi
            logger.warning("SMS fallback muvaffaqiyatsiz (appt=%s)", appt.pk, exc_info=True)

        # notify() → DB + WS; post_save ko'prik → Telegram (chat bo'lsa)
        notify(
            recipient=appt.client,
            ntype=NotificationType.BOOKING_REMINDER,
            title="Navbat eslatmasi",
            body=body,
            link=f"/c/bookings/{appt.pk}",
        )
        Appointment.objects.filter(pk=appt.pk).update(reminded_at=timezone.now())
        sent += 1
    return sent
