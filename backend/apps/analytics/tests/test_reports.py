"""Hisobot xizmatlari testlari (barber_daily, salon_period, admin_period)."""

from datetime import time, timedelta

import pytest
from django.utils import timezone

from apps.analytics.services.reports import admin_period, barber_daily, salon_period
from apps.barbers.factories import BarberProfileFactory
from apps.bookings.factories import AppointmentFactory
from apps.bookings.models import AppointmentStatus

pytestmark = pytest.mark.django_db


class TestBarberDaily:
    def test_revenue_counts_completed_only(self):
        barber = BarberProfileFactory()
        AppointmentFactory(
            barber=barber, date=timezone.localdate(), status=AppointmentStatus.COMPLETED
        )
        AppointmentFactory(
            barber=barber,
            date=timezone.localdate(),
            start_time=time(11, 0),
            status=AppointmentStatus.CONFIRMED,
        )
        AppointmentFactory(
            barber=barber,
            date=timezone.localdate(),
            start_time=time(12, 0),
            status=AppointmentStatus.CANCELLED,
        )

        report = barber_daily(barber, timezone.localdate())

        assert report["totals"]["all"] == 3
        assert report["totals"]["by_status"]["completed"] == 1
        assert report["totals"]["revenue"] == 50000  # faqat bajarilgan navbat
        assert len(report["rows"]) == 3

    def test_only_that_day_and_barber(self):
        barber = BarberProfileFactory()
        other = BarberProfileFactory()
        AppointmentFactory(barber=other, date=timezone.localdate())
        AppointmentFactory(barber=barber, date=timezone.localdate() + timedelta(days=1))

        report = barber_daily(barber, timezone.localdate())

        assert report["totals"]["all"] == 0

    def test_rows_sorted_by_time(self):
        barber = BarberProfileFactory()
        AppointmentFactory(barber=barber, date=timezone.localdate(), start_time=time(12, 0))
        AppointmentFactory(barber=barber, date=timezone.localdate(), start_time=time(9, 0))

        report = barber_daily(barber, timezone.localdate())

        assert [row["time"] for row in report["rows"]] == ["09:00", "12:00"]


class TestSalonPeriod:
    def test_grouped_by_barber_with_totals(self):
        from apps.salons.factories import SalonFactory

        salon = SalonFactory()
        b1 = BarberProfileFactory(salon=salon)
        b2 = BarberProfileFactory(salon=salon)
        AppointmentFactory(barber=b1, status=AppointmentStatus.COMPLETED)
        AppointmentFactory(barber=b1, start_time=time(11, 0), status=AppointmentStatus.PENDING)
        AppointmentFactory(barber=b2, status=AppointmentStatus.COMPLETED)
        # boshqa salon — hisobotga kirmasligi kerak
        AppointmentFactory(status=AppointmentStatus.COMPLETED)

        start = timezone.localdate() - timedelta(days=1)
        end = timezone.localdate() + timedelta(days=1)
        report = salon_period(salon, start, end)

        assert report["totals"]["total"] == 3
        assert report["totals"]["completed"] == 2
        assert report["totals"]["revenue"] == 100000
        by_name = {row["barber_id"]: row for row in report["rows"]}
        assert by_name[b1.pk]["total"] == 2
        assert by_name[b1.pk]["revenue"] == 50000

    def test_period_boundaries(self):
        from apps.salons.factories import SalonFactory

        salon = SalonFactory()
        barber = BarberProfileFactory(salon=salon)
        today = timezone.localdate()
        AppointmentFactory(barber=barber, date=today - timedelta(days=3))
        AppointmentFactory(barber=barber, date=today)

        report = salon_period(salon, today - timedelta(days=3), today)

        assert report["totals"]["total"] == 2


class TestAdminPeriod:
    def test_per_salon_rows(self):
        from apps.salons.factories import SalonFactory

        salon1 = SalonFactory()
        salon2 = SalonFactory()
        b1 = BarberProfileFactory(salon=salon1)
        b2 = BarberProfileFactory(salon=salon2)
        AppointmentFactory(barber=b1, status=AppointmentStatus.COMPLETED)
        AppointmentFactory(barber=b2, status=AppointmentStatus.COMPLETED)
        AppointmentFactory(barber=b2, start_time=time(11, 0), status=AppointmentStatus.NO_SHOW)

        start = timezone.localdate() - timedelta(days=1)
        end = timezone.localdate() + timedelta(days=1)
        report = admin_period(start, end)

        assert {row["salon_id"] for row in report["rows"]} == {salon1.pk, salon2.pk}
        assert report["totals"]["total"] == 3
        assert report["totals"]["revenue"] == 100000
