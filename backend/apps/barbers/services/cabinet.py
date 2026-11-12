"""Sartarosh kabineti biznes mantiq (bosqich 5).

Egalik tekshiruvlari (IDOR) view'dagi `get_object_or_404(...,
barber__user=user)` bilan birga bu yerda ham qo'llanadi (ikki qatlam).
"""

from datetime import date

from django.db import transaction

from apps.barbers.models import BarberProfile
from apps.barbers.services.exceptions import CabinetValidationError
from apps.core.services.audit import log_action
from apps.schedule.models import DayOff, ScheduleBreak, Weekday, WorkSchedule
from apps.services.models import Service, ServiceOwner


def get_profile(user) -> BarberProfile | None:
    """User'ning sartarosh profili (yo'q bo'lsa None)."""
    return BarberProfile.objects.filter(user=user).first()


def create_profile(
    user, *, bio: str = "", experience_years: int = 0, specialties=None
) -> BarberProfile:
    """Onboarding: sartarosh profili yaratadi (salon keyin bog'lanadi)."""
    if get_profile(user) is not None:
        raise CabinetValidationError("Profil allaqachon mavjud.")

    profile = BarberProfile.objects.create(user=user, bio=bio, experience_years=experience_years)
    if specialties:
        profile.specialties.set(specialties)

    log_action(
        actor=user,
        action="barber_profile_created",
        model_name="barbers.BarberProfile",
        object_id=profile.pk,
    )
    return profile


def update_profile(user, *, data: dict) -> BarberProfile:
    """Profil tahriri (bio, tajriba, mutaxassisliklar, portfolio)."""
    profile = get_profile(user)
    if profile is None:
        raise CabinetValidationError("Sartarosh profili topilmadi.")

    allowed = ("bio", "experience_years", "portfolio_images")
    for field in allowed:
        if field in data:
            setattr(profile, field, data[field])
    profile.save(update_fields=(*allowed, "updated_at"))

    if "specialties" in data and data["specialties"] is not None:
        profile.specialties.set(data["specialties"])
    return profile


def set_active_now(user, *, is_active: bool) -> BarberProfile:
    """Faol/Nofaol tugmasi (kun boshida ochish, oxirida yopish)."""
    profile = get_profile(user)
    if profile is None:
        raise CabinetValidationError("Sartarosh profili topilmadi.")

    profile.is_active_now = is_active
    profile.save(update_fields=("is_active_now", "updated_at"))
    log_action(
        actor=user,
        action="barber_active_toggled",
        model_name="barbers.BarberProfile",
        object_id=profile.pk,
        payload={"is_active": is_active},
    )
    return profile


# --- Jadval ---


def week_schedule(user) -> list[WorkSchedule]:
    """User'ning haftalik jadvali (dushanbadan yakshanbagacha tartibda)."""
    profile = get_profile(user)
    if profile is None:
        raise CabinetValidationError("Sartarosh profili topilmadi.")
    return list(WorkSchedule.objects.filter(barber=profile).order_by("weekday"))


def replace_week_schedule(user, rows: list[dict]) -> list[WorkSchedule]:
    """Haftalik jadvalni almashtiradi (update_or_create — tanaffuslar saqlanadi)."""
    profile = get_profile(user)
    if profile is None:
        raise CabinetValidationError("Sartarosh profili topilmadi.")

    weekdays = {row["weekday"] for row in rows}
    if len(weekdays) != len(rows):
        raise CabinetValidationError("Har hafta kuni faqat bir marta beriladi.")
    for row in rows:
        if row["weekday"] not in Weekday.values:
            raise CabinetValidationError("Noma'lum hafta kuni.")

    with transaction.atomic():
        schedules = [
            WorkSchedule.objects.update_or_create(
                barber=profile,
                weekday=row["weekday"],
                defaults={
                    "start_time": row["start_time"],
                    "end_time": row["end_time"],
                    "is_working": row.get("is_working", True),
                },
            )[0]
            for row in rows
        ]
    return schedules


def add_break(user, *, weekday: int, start_time, end_time) -> ScheduleBreak:
    """Ish kuniga tanaffus qo'shadi (jadval mavjud bo'lishi shart)."""
    schedule = WorkSchedule.objects.filter(barber__user=user, weekday=weekday).first()
    if schedule is None:
        raise CabinetValidationError("Bu kun uchun ish jadvali topilmadi.")
    if start_time >= end_time:
        raise CabinetValidationError("Tanaffus boshlanishi tugashidan oldin bo'lishi kerak.")
    if not (schedule.start_time <= start_time < schedule.end_time):
        raise CabinetValidationError("Tanaffus ish vaqti ichida bo'lishi kerak.")
    if not (schedule.start_time < end_time <= schedule.end_time):
        raise CabinetValidationError("Tanaffus ish vaqti ichida bo'lishi kerak.")

    return ScheduleBreak.objects.create(schedule=schedule, start_time=start_time, end_time=end_time)


def remove_break(user, *, break_id: int) -> None:
    """Tanaffusni o'chiradi (o'z jadvalidan)."""
    deleted, _ = ScheduleBreak.objects.filter(pk=break_id, schedule__barber__user=user).delete()
    if not deleted:
        raise CabinetValidationError("Tanaffus topilmadi.")


def add_day_off(user, *, day: date, reason: str = "") -> DayOff:
    """Bir martalik dam olish kuni qo'shadi."""
    profile = get_profile(user)
    if profile is None:
        raise CabinetValidationError("Sartarosh profili topilmadi.")
    return DayOff.objects.get_or_create(barber=profile, date=day, defaults={"reason": reason})[0]


def remove_day_off(user, *, day_off_id: int) -> None:
    deleted, _ = DayOff.objects.filter(pk=day_off_id, barber__user=user).delete()
    if not deleted:
        raise CabinetValidationError("Dam olish kuni topilmadi.")


# --- Xizmatlar ---


def create_service(user, *, data: dict) -> Service:
    """Sartarosh xizmati yaratadi (owner_type=BARBER, salon=None)."""
    profile = get_profile(user)
    if profile is None:
        raise CabinetValidationError("Sartarosh profili topilmadi.")

    return Service.objects.create(
        owner_type=ServiceOwner.BARBER,
        barber=profile,
        salon=None,
        category=data["category"],
        name=data["name"],
        duration_min=data["duration_min"],
        price=data.get("price", 0),
        description=data.get("description", ""),
    )
