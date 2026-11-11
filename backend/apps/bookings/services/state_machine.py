"""Navbat holat mashinasi (state machine).

Yagona ruxsat etilgan o'tishlar xaritasi — barcha amallar (confirm,
reject, cancel, complete, no-show) shu matritsa orqali o'tadi.

    PENDING   -> CONFIRMED, REJECTED, CANCELLED
    CONFIRMED -> COMPLETED, NO_SHOW, CANCELLED
    COMPLETED / REJECTED / CANCELLED / NO_SHOW -> terminal (o'tish yo'q)
"""

from django.db import transaction

from apps.bookings.models import Appointment, AppointmentHistory, AppointmentStatus
from apps.bookings.services.exceptions import InvalidTransition
from apps.core.services.audit import log_action

TRANSITIONS: dict[str, frozenset[str]] = {
    AppointmentStatus.PENDING: frozenset(
        {
            AppointmentStatus.CONFIRMED,
            AppointmentStatus.REJECTED,
            AppointmentStatus.CANCELLED,
        }
    ),
    AppointmentStatus.CONFIRMED: frozenset(
        {
            AppointmentStatus.COMPLETED,
            AppointmentStatus.NO_SHOW,
            AppointmentStatus.CANCELLED,
        }
    ),
    AppointmentStatus.COMPLETED: frozenset(),
    AppointmentStatus.REJECTED: frozenset(),
    AppointmentStatus.CANCELLED: frozenset(),
    AppointmentStatus.NO_SHOW: frozenset(),
}


def can_transition(old_status: str, new_status: str) -> bool:
    """Eski holatdan yangi holatga o'tish mumkinligini qaytaradi."""
    return new_status in TRANSITIONS.get(old_status, frozenset())


def transition(
    appointment: Appointment,
    new_status: str,
    *,
    changed_by=None,
    comment: str = "",
) -> Appointment:
    """Holatni o'zgartiradi: validatsiya + saqlash + tarix yozuvi + audit.

    Noto'g'ri o'tishda InvalidTransition (409) ko'taradi — bazada hech
    narsa o'zgarmaydi.
    """
    old_status = appointment.status
    if new_status == old_status or not can_transition(old_status, new_status):
        raise InvalidTransition(
            detail=f'"{old_status}" -> "{new_status}" holat o\'tishi mumkin emas.'
        )

    with transaction.atomic():
        appointment.status = new_status
        appointment.save(update_fields=("status", "updated_at"))
        AppointmentHistory.objects.create(
            appointment=appointment,
            old_status=old_status,
            new_status=new_status,
            changed_by=changed_by,
            comment=comment,
        )

    log_action(
        actor=changed_by,
        action=f"appointment_{new_status}",
        model_name="bookings.Appointment",
        object_id=appointment.pk,
        payload={"old_status": old_status, "new_status": new_status},
    )
    return appointment
