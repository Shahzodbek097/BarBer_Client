"""Bosqich 2: WorkSchedule, ScheduleBreak, DayOff model testlari."""

from datetime import timedelta

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.schedule.factories import DayOffFactory, ScheduleBreakFactory, WorkScheduleFactory
from apps.schedule.models import DayOff, ScheduleBreak, Weekday, WorkSchedule

pytestmark = pytest.mark.django_db


class TestWeekday:
    def test_choice_values(self):
        assert Weekday.MONDAY == 0
        assert Weekday.SUNDAY == 6


class TestWorkSchedule:
    def test_str(self):
        ws = WorkScheduleFactory(barber__user__full_name="Usta")

        assert "Usta" in str(ws)
        assert "09:00" in str(ws)

    def test_one_schedule_per_weekday(self):
        ws = WorkScheduleFactory()

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                WorkSchedule.objects.create(
                    barber=ws.barber,
                    weekday=ws.weekday,
                    start_time=ws.start_time,
                    end_time=ws.end_time,
                )

    def test_other_weekdays_allowed(self):
        barber = WorkScheduleFactory(weekday=Weekday.MONDAY).barber
        ws2 = WorkScheduleFactory(barber=barber, weekday=Weekday.TUESDAY)

        assert ws2.weekday == Weekday.TUESDAY

    def test_start_before_end_required(self):
        ws = WorkScheduleFactory()

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                WorkSchedule.objects.filter(pk=ws.pk).update(
                    start_time=ws.end_time, end_time=ws.start_time
                )

    def test_breaks_related(self):
        ws = WorkScheduleFactory()
        br = ScheduleBreakFactory(schedule=ws)

        assert list(ws.breaks.all()) == [br]


class TestScheduleBreak:
    def test_str(self):
        br = ScheduleBreakFactory()

        assert "13:00" in str(br)

    def test_time_order_required(self):
        br = ScheduleBreakFactory()

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ScheduleBreak.objects.filter(pk=br.pk).update(
                    start_time=br.end_time, end_time=br.start_time
                )


class TestDayOff:
    def test_str(self):
        do = DayOffFactory(barber__user__full_name="Usta")

        assert "Usta" in str(do)

    def test_unique_barber_date(self):
        do = DayOffFactory()

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                DayOff.objects.create(barber=do.barber, date=do.date, reason="x")

    def test_reason_optional(self):
        do = DayOff.objects.create(
            barber=DayOffFactory().barber,
            date=timezone.localdate() + timedelta(days=10),
        )

        assert do.reason == ""
