"""Navbat yaratish va holat amallari (bosqich 4 domen mantiqi).

Qoidalar:
- biznes logika faqat shu qatlamda; view/bot faqat chaqiradi (bosqich 5)
- slot tekshiruvi `schedule.services.slots` dvigateli orqali — band
  oraliqlar (`busy_intervals`) argument sifatida uzatiladi
- ikkinchi bandlovni DB constraint
  (`appointment_active_slot_unique`) to'sadi -> IntegrityError
  SlotUnavailable (409) ga aylanadi
"""

from datetime import date, datetime, time

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.barbers.models import BarberStatus
from apps.bookings.models import (
    Appointment,
    AppointmentHistory,
    AppointmentSource,
    AppointmentStatus,
)
from apps.bookings.services.exceptions import (
    AppointmentNotOwner,
    BookingValidationError,
    SlotUnavailable,
)
from apps.bookings.services.state_machine import transition
from apps.core.services.audit import log_action
from apps.schedule.services import slots as slot_engine
from apps.services.models import ServiceOwner

# Band hisoblanMAYdigan holatlar (constraint bilan bir xil mantik)
FREE_STATUSES = (AppointmentStatus.CANCELLED, AppointmentStatus.REJECTED)


def busy_intervals(barber, day: date) -> list[tuple[time, time]]:
    """Sartaroshning shu kundagi band oraliqlari (slot dvigatelga argument).

    CANCELLED va REJECTED navbatlar slotni egallamaydi (constraint
    mantig'i bilan mos).
    """
    qs = (
        Appointment.objects.filter(barber=barber, date=day)
        .exclude(status__in=FREE_STATUSES)
        .order_by("start_time")
    )
    return [(a.start_time, a.end_time) for a in qs]


def list_client_appointments(user, *, status: str = ""):
    """Mijozning O'Z navbatlari (IDOR himoyasi: client=user).

    Bosqich 5 API uchun: QuerySet izolyatsiyasi service qatlamida.
    """
    qs = Appointment.objects.filter(client=user).select_related("barber__user", "service", "salon")
    if status:
        qs = qs.filter(status=status)
    return qs.order_by("-date", "-start_time")


def list_barber_appointments(user, *, status: str = "", day=None):
    """Sartaroshning O'Z navbatlari (kelib tushganlar ro'yxati)."""
    profile = getattr(user, "barber_profile", None)
    if profile is None:
        raise BookingValidationError("Sartarosh profili topilmadi.")

    qs = Appointment.objects.filter(barber=profile).select_related("client", "service", "salon")
    if status:
        qs = qs.filter(status=status)
    if day is not None:
        qs = qs.filter(date=day)
    return qs.order_by("date", "start_time")


def _local_now() -> datetime:
    """Naive lokal joriy vaqt (jadval vaqt maydonlari naive lokalda)."""
    return timezone.localtime().replace(tzinfo=None)


def _match_slot(barber, day: date, start_time: time, duration_min: int, *, busy, now):
    """Berilgan boshlanish vaqtiga mos bo'sh slot; yo'q bo'lsa 409."""
    slots = slot_engine.available_slots(barber, day, duration_min, busy=busy, now=now)
    for slot in slots:
        if slot.start == start_time:
            return slot
    raise SlotUnavailable()


def _validate_barber(barber, *, online: bool) -> None:
    if barber.is_deleted:
        raise BookingValidationError("Sartarosh topilmadi.")
    if barber.status != BarberStatus.APPROVED:
        raise BookingValidationError("Sartarosh hozir tasdiqlanmagan.")
    if online and not barber.is_active_now:
        raise BookingValidationError("Sartarosh hozir nofaol. Keyinroq urinib ko'ring.")


def _validate_service(barber, service) -> None:
    if not service.is_active:
        raise BookingValidationError("Bu xizmat nofaol.")
    if service.owner_type == ServiceOwner.BARBER:
        if service.barber_id != barber.id:
            raise BookingValidationError("Bu xizmat ushbu sartaroshga tegishli emas.")
    elif barber.salon_id is None or service.salon_id != barber.salon_id:
        raise BookingValidationError("Bu xizmat ushbu salonning sartaroshiga tegishli emas.")


def _validate_date_time(day: date, start_time: time, *, now: datetime) -> None:
    if day < now.date():
        raise BookingValidationError("O'tgan sanaga navbat olib bo'lmaydi.")
    if day == now.date() and start_time <= now.time():
        raise BookingValidationError("O'tgan vaqtga navbat olib bo'lmaydi.")


def create_appointment(
    *,
    client,
    barber,
    service,
    day: date,
    start_time: time,
    note: str = "",
    source: str = AppointmentSource.ONLINE,
) -> Appointment:
    """Yangi navbat yaratadi (ikki marta bandlovni constraint to'sadi).

    Oqim: validatsiyalar -> slot dvigateli -> INSERT ->
    AppointmentHistory (yaratilish yozuvi) -> audit.

    Qaytadi: yaratilgan Appointment (status=PENDING, narx muzlatilgan).
    Race: bir slotga 10 kishi bir paytda kirsa — 1 g'alaba, 9 SlotUnavailable.
    """
    now = _local_now()
    _validate_barber(barber, online=(source == AppointmentSource.ONLINE))
    _validate_service(barber, service)
    _validate_date_time(day, start_time, now=now)

    slot = _match_slot(
        barber,
        day,
        start_time,
        service.duration_min,
        busy=busy_intervals(barber, day),
        now=now,
    )

    try:
        with transaction.atomic():
            appointment = Appointment.objects.create(
                client=client,
                barber=barber,
                salon=barber.salon,
                service=service,
                date=day,
                start_time=slot.start,
                end_time=slot.end,
                source=source,
                price=service.price,
                client_note=note,
            )
            AppointmentHistory.objects.create(
                appointment=appointment,
                old_status=None,
                new_status=AppointmentStatus.PENDING,
                changed_by=client,
                comment="Navbat yaratildi.",
            )
    except IntegrityError:
        # appointment_active_slot_unique: slot kimningdir bo'ldi
        raise SlotUnavailable() from None

    log_action(
        actor=client,
        action="appointment_created",
        model_name="bookings.Appointment",
        object_id=appointment.pk,
        payload={
            "barber_id": barber.id,
            "service_id": service.id,
            "date": str(day),
            "start": str(start_time),
        },
    )
    return appointment


def _ensure_barber(appointment: Appointment, by) -> None:
    """Amal faqat o'z navbatining sartaroshiga ruxsat."""
    if by is None or appointment.barber.user_id != by.id:
        raise AppointmentNotOwner()


def _ensure_participant(appointment: Appointment, by) -> None:
    """Bekor qilish: navbat egasi (mijoz) yoki sartaroshi."""
    if by is None:
        raise AppointmentNotOwner()
    if appointment.client_id != by.id and appointment.barber.user_id != by.id:
        raise AppointmentNotOwner()


def confirm(appointment: Appointment, *, by) -> Appointment:
    """Sartarosh navbatni tasdiqlaydi: PENDING -> CONFIRMED."""
    _ensure_barber(appointment, by)
    return transition(
        appointment, AppointmentStatus.CONFIRMED, changed_by=by, comment="Sartarosh tasdiqladi."
    )


def reject(appointment: Appointment, *, by, reply: str = "") -> Appointment:
    """Sartarosh navbatni rad etadi: PENDING -> REJECTED."""
    _ensure_barber(appointment, by)
    if reply:
        appointment.barber_reply = reply
        appointment.save(update_fields=("barber_reply",))
    return transition(appointment, AppointmentStatus.REJECTED, changed_by=by, comment=reply)


def cancel(appointment: Appointment, *, by, comment: str = "") -> Appointment:
    """Mijoz yoki sartarosh navbatni bekor qiladi (PENDING/CONFIRMED)."""
    _ensure_participant(appointment, by)
    return transition(appointment, AppointmentStatus.CANCELLED, changed_by=by, comment=comment)


def complete(appointment: Appointment, *, by) -> Appointment:
    """Xizmat bajarildi: CONFIRMED -> COMPLETED."""
    _ensure_barber(appointment, by)
    return transition(
        appointment, AppointmentStatus.COMPLETED, changed_by=by, comment="Xizmat bajarildi."
    )


def mark_no_show(appointment: Appointment, *, by) -> Appointment:
    """Mijoz kelmadi: CONFIRMED -> NO_SHOW."""
    _ensure_barber(appointment, by)
    return transition(
        appointment, AppointmentStatus.NO_SHOW, changed_by=by, comment="Mijoz kelmadi."
    )


def propose_new_time(appointment: Appointment, *, by, day: date, start_time: time) -> Appointment:
    """Sartarosh boshqa vaqt taklif qiladi (holat PENDING qoladi).

    Navbat yangi vaqtga ko'chadi; mijoz yangi vaqtni barber_reply
    maydonida ko'radi. Taklifni qabul qilish = navbatni qoldirish,
    rad etish = bekor qilish. O'z eskirgan oraliqi yangi slotga
    to'siq emas (busy ro'yxatidan chetlatiladi).
    """
    _ensure_barber(appointment, by)
    return _move_to_slot(
        appointment,
        by=by,
        day=day,
        start_time=start_time,
        reply=f"Yangi vaqt taklif qilindi: {day:%d.%m.%Y} {start_time:%H:%M}.",
        comment=f"Yangi vaqt taklif qilindi: {day} {start_time}.",
    )


def reschedule(appointment: Appointment, *, by, day: date, start_time: time) -> Appointment:
    """Mijoz o'z PENDING navbatini boshqa bo'sh vaqtga ko'chiradi."""
    if by is None or appointment.client_id != by.id:
        raise AppointmentNotOwner()
    if appointment.status != AppointmentStatus.PENDING:
        raise BookingValidationError("Faqat kutilayotgan (PENDING) navbatni o'zgartirish mumkin.")
    return _move_to_slot(
        appointment,
        by=by,
        day=day,
        start_time=start_time,
        reply="",
        comment=f"Mijoz vaqtni o'zgartirdi: {day} {start_time}.",
    )


def _move_to_slot(
    appointment: Appointment,
    *,
    by,
    day: date,
    start_time: time,
    reply: str,
    comment: str,
) -> Appointment:
    """Navbatni yangi bo'sh slotga ko'chiradi (propose/reschedule ortak).

    Slot band bo'lsa SlotUnavailable (409); yangi slotda yana biror
    navbat paydo bo'lsa DB constraint to'sadi (IntegrityError → 409).
    """
    now = _local_now()
    _validate_date_time(day, start_time, now=now)

    duration_min = appointment.service.duration_min
    busy = [
        (a.start_time, a.end_time)
        for a in Appointment.objects.filter(barber=appointment.barber, date=day)
        .exclude(status__in=FREE_STATUSES)
        .exclude(pk=appointment.pk)
        .order_by("start_time")
    ]
    slot = _match_slot(appointment.barber, day, start_time, duration_min, busy=busy, now=now)

    try:
        with transaction.atomic():
            appointment.date = day
            appointment.start_time = slot.start
            appointment.end_time = slot.end
            if reply:
                appointment.barber_reply = reply
            appointment.save(
                update_fields=("date", "start_time", "end_time", "barber_reply", "updated_at")
            )
            AppointmentHistory.objects.create(
                appointment=appointment,
                old_status=appointment.status,
                new_status=appointment.status,
                changed_by=by,
                comment=comment,
            )
    except IntegrityError:
        raise SlotUnavailable() from None

    log_action(
        actor=by,
        action="appointment_time_proposed",
        model_name="bookings.Appointment",
        object_id=appointment.pk,
        payload={"date": str(day), "start": str(start_time)},
    )
    return appointment
