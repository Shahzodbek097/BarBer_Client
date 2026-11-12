"""Salon moderatsiyasi (super admin amallari, bosqich 5).

Import yo'nalishi: salons pastda — accounts import qilishi OK.
Statistikalar `bookings/services/stats.py`da (yuqori qatlam).
"""

from rest_framework.exceptions import APIException

from apps.core.services.audit import log_action
from apps.salons.models import Salon, SalonStatus


class ModerationError(APIException):
    status_code = 400
    default_detail = "Moderatsiya amali bajarilmadi."
    default_code = "moderation_invalid"


def approve_salon(salon_id: int) -> Salon:
    """PENDING salonni tasdiqlaydi (katalogda ko'rinadigan bo'ladi)."""
    salon = Salon.objects.filter(pk=salon_id).first()
    if salon is None:
        raise ModerationError("Salon topilmadi.")
    if salon.status == SalonStatus.APPROVED:
        raise ModerationError("Salon allaqachon tasdiqlangan.")

    salon.status = SalonStatus.APPROVED
    salon.save(update_fields=("status", "updated_at"))
    log_action(
        actor=None,
        action="salon_approved",
        model_name="salons.Salon",
        object_id=salon.pk,
    )
    return salon


def block_salon(salon_id: int) -> Salon:
    """Salonni bloklaydi (katalogdan yashiriladi)."""
    salon = Salon.objects.filter(pk=salon_id).first()
    if salon is None:
        raise ModerationError("Salon topilmadi.")
    if salon.status == SalonStatus.BLOCKED:
        raise ModerationError("Salon allaqachon bloklangan.")

    salon.status = SalonStatus.BLOCKED
    salon.save(update_fields=("status", "updated_at"))
    log_action(
        actor=None,
        action="salon_blocked",
        model_name="salons.Salon",
        object_id=salon.pk,
    )
    return salon
