"""Slot dvigateli: bir kun uchun bo'sh vaqt slotlarini hisoblash.

Plan qoidasi (modul qoidalari §3.4): dvigatel `bookings` app'ini bilmaydi —
band vaqt ro'yxati oddiy (start, end) juftliklari sifatida argumentga
keladi. Shu tufayli dvigatel `schedule` qatlamida yashaydi va yuqoridagi
app'lar (bookings, katalog) uni o'z ma'lumotlari bilan chaqiradi.

Yarim ochiq oraliq mantig'i: [start, end) — slot yoki tanaffus
aynan tugaganda boshlanadigan slot BAAR ("13:00-14:00 tanaffusdan keyin
14:00 sloti mavjud"), aynan boshlanganda tugaydigan slot ham BAAR.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from django.utils import timezone

DEFAULT_STEP_MIN = 15  # slotlar 15 daqiqalik panjara


@dataclass(frozen=True, order=True)
class Slot:
    """Bitta bo'sh vaqt: boshlanish va davomiylik bilan tugash."""

    start: time
    end: time


def _overlaps(a_start: time, a_end: time, b_start: time, b_end: time) -> bool:
    """Ikki [start, end) oraliq kesishadi ("aynan tegish" emas)."""
    return a_start < b_end and b_start < a_end


def compute_day_slots(
    day: date,
    duration_min: int,
    work_start: time | None,
    work_end: time | None,
    *,
    breaks: Iterable[tuple[time, time]] = (),
    busy: Iterable[tuple[time, time]] = (),
    step_min: int = DEFAULT_STEP_MIN,
    now: datetime | None = None,
) -> list[Slot]:
    """Bir ish kuni uchun barcha bo'sh slot boshlanishlarini qaytaradi.

    Args:
        day: sana (o'tgan slotlarni filtrlash uchun kerak — `now` bilan).
        duration_min: xizmat davomiyligi (daqiqada).
        work_start/work_end: ish kunining oralig'i; None → dam olish kuni ([]).
        breaks: tanaffuslar ro'yxati [(start, end), ...].
        busy: band oraliqlar ro'yxati [(start, end), ...] — mavjud
            navbatlar (chaqiruvchi beradi, dvigatel DB'ga kirbilmaydi).
        step_min: kandidat boshlanishlar panjarasi (daqiqada).
        now: joriy moment (naive lokal); `day <= now.date()` bo'lganda
            allaqachon boshlangan slotlar chetlatiladi (butun kun
            o'tgan bo'lsa ro'yxat bo'sh). None → filtrlash yo'q (testlar).

    Returns:
        Slot'lar ro'yxati (start bo'yicha o'sish tartibida).
    """
    if duration_min <= 0 or step_min <= 0 or work_start is None or work_end is None:
        return []

    duration = timedelta(minutes=duration_min)
    step = timedelta(minutes=step_min)
    base = datetime.combine(date.min, work_start)
    last_start = datetime.combine(date.min, work_end) - duration
    if last_start < base:
        return []  # ish kuni xizmat davomiylikdan qisqa

    break_list = list(breaks)
    busy_list = list(busy)

    slots: list[Slot] = []
    t = base
    while t <= last_start:
        end_dt = t + duration
        start_t, end_t = t.time(), end_dt.time()
        in_break = any(_overlaps(start_t, end_t, b, e) for b, e in break_list)
        is_busy = any(_overlaps(start_t, end_t, b, e) for b, e in busy_list)
        slot_dt = datetime.combine(day, start_t)
        in_past = now is not None and day <= now.date() and slot_dt <= now
        if not in_break and not is_busy and not in_past:
            slots.append(Slot(start_t, end_t))
        t += step
    return slots


def day_work_interval(barber, day: date) -> tuple[time, time] | None:
    """Sartaroshning shu kunga mos ish oralig'i; dam olish kuni → None.

    DayOff mavjud bo'lsa, hafta kuni jadvalidan qat'i nazar dam olish.
    """
    from apps.schedule.models import DayOff, WorkSchedule

    if DayOff.objects.filter(barber=barber, date=day).exists():
        return None

    schedule = WorkSchedule.objects.filter(barber=barber, weekday=day.weekday()).first()
    if schedule is None or not schedule.is_working:
        return None
    return schedule.start_time, schedule.end_time


def day_breaks(barber, day: date) -> list[tuple[time, time]]:
    """Shu hafta kuniga tegishli tanaffuslar (start bo'yicha tartibda)."""
    from apps.schedule.models import ScheduleBreak

    return list(
        ScheduleBreak.objects.filter(schedule__barber=barber, schedule__weekday=day.weekday())
        .order_by("start_time")
        .values_list("start_time", "end_time")
    )


def available_slots(
    barber,
    day: date,
    duration_min: int,
    *,
    busy: Iterable[tuple[time, time]] = (),
    step_min: int = DEFAULT_STEP_MIN,
    now: datetime | None = None,
) -> list[Slot]:
    """Sartaroshning shu kundagi bo'sh slotlari (jadval + tanaffus + band).

    `busy` — chaqiruvchi yig'ib kelgan band oraliqlar (mavjud aktiv
    navbatlar). `now` berilmasa joriy lokal vaqt olinadi (o'tgan slotlar
    chetlatiladi; testlarda muqobil vaqt berish mumkin).
    """
    work = day_work_interval(barber, day)
    if work is None:
        return []

    if now is None:
        now = timezone.localtime().replace(tzinfo=None)

    return compute_day_slots(
        day,
        duration_min,
        work[0],
        work[1],
        breaks=day_breaks(barber, day),
        busy=busy,
        step_min=step_min,
        now=now,
    )


__all__ = ["DEFAULT_STEP_MIN", "Slot", "available_slots", "compute_day_slots"]
