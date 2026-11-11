"""Bosqich 4: slot dvigateli DB integratsiyasi (jadval, tanaffus, dam olish)."""

from datetime import datetime, time, timedelta

import pytest
from django.utils import timezone

from apps.barbers.factories import BarberProfileFactory
from apps.schedule.factories import DayOffFactory, ScheduleBreakFactory, WorkScheduleFactory
from apps.schedule.services import slots

pytestmark = pytest.mark.django_db


def _tomorrow():
    return timezone.localdate() + timedelta(days=1)


def _schedule_for(barber, day, **kwargs):
    """Berilgan sana hafta kuniga mos WorkSchedule yaratadi."""
    return WorkScheduleFactory(barber=barber, weekday=day.weekday(), **kwargs)


class TestDayWorkInterval:
    def test_returns_interval(self):
        barber = BarberProfileFactory()
        day = _tomorrow()
        _schedule_for(barber, day, start_time=time(9, 0), end_time=time(18, 0))

        assert slots.day_work_interval(barber, day) == (time(9, 0), time(18, 0))

    def test_no_schedule_returns_none(self):
        barber = BarberProfileFactory()

        assert slots.day_work_interval(barber, _tomorrow()) is None

    def test_not_working_returns_none(self):
        barber = BarberProfileFactory()
        day = _tomorrow()
        _schedule_for(barber, day, is_working=False)

        assert slots.day_work_interval(barber, day) is None

    def test_day_off_overrides_schedule(self):
        barber = BarberProfileFactory()
        day = _tomorrow()
        _schedule_for(barber, day)
        DayOffFactory(barber=barber, date=day)

        assert slots.day_work_interval(barber, day) is None

    def test_day_off_other_day_no_effect(self):
        barber = BarberProfileFactory()
        day = _tomorrow()
        _schedule_for(barber, day)
        DayOffFactory(barber=barber, date=day + timedelta(days=3))

        assert slots.day_work_interval(barber, day) is not None


class TestDayBreaks:
    def test_returns_breaks_of_that_weekday(self):
        barber = BarberProfileFactory()
        day = _tomorrow()
        schedule = _schedule_for(barber, day)
        ScheduleBreakFactory(schedule=schedule, start_time=time(13, 0), end_time=time(14, 0))

        assert slots.day_breaks(barber, day) == [(time(13, 0), time(14, 0))]

    def test_breaks_of_other_weekday_not_included(self):
        barber = BarberProfileFactory()
        day = _tomorrow()
        other_schedule = _schedule_for(barber, day + timedelta(days=2))
        ScheduleBreakFactory(schedule=other_schedule)

        assert slots.day_breaks(barber, day) == []

    def test_multiple_breaks_sorted(self):
        barber = BarberProfileFactory()
        day = _tomorrow()
        schedule = _schedule_for(barber, day)
        ScheduleBreakFactory(schedule=schedule, start_time=time(16, 0), end_time=time(16, 30))
        ScheduleBreakFactory(schedule=schedule, start_time=time(13, 0), end_time=time(14, 0))

        assert slots.day_breaks(barber, day) == [
            (time(13, 0), time(14, 0)),
            (time(16, 0), time(16, 30)),
        ]


class TestAvailableSlots:
    def test_combines_schedule_breaks_and_busy(self):
        barber = BarberProfileFactory()
        day = _tomorrow()
        schedule = _schedule_for(barber, day, start_time=time(9, 0), end_time=time(12, 0))
        ScheduleBreakFactory(schedule=schedule, start_time=time(10, 0), end_time=time(10, 30))

        result = slots.available_slots(barber, day, 30, busy=[(time(9, 0), time(9, 30))])
        starts = [s.start for s in result]

        assert time(9, 0) not in starts  # band argument: 09:00-09:30
        assert time(9, 30) in starts  # 09:30-10:00 band tugaganida boshlanadi
        assert time(9, 45) not in starts  # 09:45-10:15 tanaffusga tegadi
        assert time(10, 30) in starts  # tanaffus tugagach yana ochiladi
        assert time(11, 30) in starts  # oxirgi: 11:30-12:00

    def test_day_off_yields_empty(self):
        barber = BarberProfileFactory()
        day = _tomorrow()
        _schedule_for(barber, day)
        DayOffFactory(barber=barber, date=day)

        assert slots.available_slots(barber, day, 30) == []

    def test_now_defaults_to_local_now(self):
        barber = BarberProfileFactory()
        today = timezone.localdate()
        _schedule_for(barber, today, start_time=time(0, 0), end_time=time(23, 0))

        result = slots.available_slots(barber, today, 30)
        expected = slots.available_slots(
            barber, today, 30, now=timezone.localtime().replace(tzinfo=None)
        )

        assert result == expected

    def test_explicit_now(self):
        barber = BarberProfileFactory()
        day = _tomorrow()
        _schedule_for(barber, day, start_time=time(9, 0), end_time=time(10, 0))

        now = datetime.combine(day, time(9, 15))

        assert [s.start for s in slots.available_slots(barber, day, 30, now=now)] == [time(9, 30)]
