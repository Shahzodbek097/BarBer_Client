"""Salon egasi profili boshqaruvi (bosqich 5)."""

from rest_framework.exceptions import APIException

from apps.core.services.audit import log_action
from apps.salons.models import Salon


class SalonError(APIException):
    status_code = 400
    default_detail = "Salon amali bajarilmadi."
    default_code = "salon_invalid"


def get_own_salon(owner) -> Salon | None:
    """User'ning salonlari (ko'p bo'lsa birinchisi)."""
    return Salon.objects.filter(owner=owner).first()


def update_salon(owner, *, data: dict) -> Salon:
    """Salon profili tahriri — status/egasi o'zgartirilmaydi (moderatsiya)."""
    salon = get_own_salon(owner)
    if salon is None:
        raise SalonError("Salon profili topilmadi.")

    allowed = (
        "name",
        "address",
        "phone",
        "description",
        "photos",
        "work_time_start",
        "work_time_end",
    )
    changed = [field for field in allowed if field in data]
    for field in changed:
        setattr(salon, field, data[field])
    if changed:
        salon.save(update_fields=(*changed, "updated_at"))

    log_action(
        actor=owner,
        action="salon_profile_updated",
        model_name="salons.Salon",
        object_id=salon.pk,
        payload={"fields": changed},
    )
    return salon
