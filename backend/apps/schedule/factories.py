"""Jadval factory'lari."""

from datetime import time, timedelta

import factory
from django.utils import timezone

from apps.barbers.factories import BarberProfileFactory
from apps.schedule.models import DayOff, ScheduleBreak, Weekday, WorkSchedule


class WorkScheduleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WorkSchedule
        django_get_or_create = ("barber", "weekday")

    barber = factory.SubFactory(BarberProfileFactory)
    weekday = Weekday.MONDAY
    start_time = time(9, 0)
    end_time = time(18, 0)


class ScheduleBreakFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ScheduleBreak

    schedule = factory.SubFactory(WorkScheduleFactory)
    start_time = time(13, 0)
    end_time = time(14, 0)


class DayOffFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DayOff
        django_get_or_create = ("barber", "date")

    barber = factory.SubFactory(BarberProfileFactory)
    date = factory.LazyFunction(lambda: timezone.localdate() + timedelta(days=7))
    reason = factory.Sequence(lambda n: f"Sabab {n + 1}")
