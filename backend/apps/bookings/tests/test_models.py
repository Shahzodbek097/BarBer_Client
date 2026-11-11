"""Bosqich 2: Appointment va AppointmentHistory testlari.

Kritik: `appointment_active_slot_unique` — bir sartarosh / bir sana /
bir vaqtga faqat BITTA aktiv navbat (CANCELLED va REJECTED mustasno).
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.accounts.factories import UserFactory
from apps.barbers.factories import BarberProfileFactory
from apps.bookings.factories import AppointmentFactory, AppointmentHistoryFactory
from apps.bookings.models import (
    AppointmentSource,
    AppointmentStatus,
)

pytestmark = pytest.mark.django_db


def _slot(appt=None):
    """Bir xil (barber, date, start_time) uchligini qaytaradi."""
    if appt is None:
        appt = AppointmentFactory()
    return {
        "barber": appt.barber,
        "date": appt.date,
        "start_time": appt.start_time,
    }


class TestAppointment:
    def test_factory_consistency(self):
        appt = AppointmentFactory()

        assert appt.status == AppointmentStatus.PENDING
        assert appt.source == AppointmentSource.ONLINE
        assert appt.service.barber == appt.barber  # xizmat shu sartaroshniki
        assert appt.salon == appt.barber.salon
        assert appt.price == appt.service.price

    def test_str(self):
        appt = AppointmentFactory(client__full_name="Mijoz")

        assert "Mijoz" in str(appt)

    def test_salon_nullable_for_independent_barber(self):
        appt = AppointmentFactory(barber__salon=None)

        assert appt.salon is None

    def test_price_frozen_at_booking(self):
        appt = AppointmentFactory()
        appt.service.price = Decimal("99999.00")
        appt.service.save()
        appt.refresh_from_db()

        assert appt.price == Decimal("50000.00")  # bandlov paytidagi narx

    def test_double_booking_active_blocked(self):
        appt = AppointmentFactory()

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                AppointmentFactory(**_slot(appt))

    def test_cancelled_slot_reusable(self):
        appt = AppointmentFactory()
        appt.status = AppointmentStatus.CANCELLED
        appt.save()

        new_appt = AppointmentFactory(**_slot(appt))  # xato bo'lmasligi kerak

        assert new_appt.pk != appt.pk

    def test_rejected_slot_reusable(self):
        appt = AppointmentFactory()
        appt.status = AppointmentStatus.REJECTED
        appt.save()

        new_appt = AppointmentFactory(**_slot(appt))

        assert new_appt.status == AppointmentStatus.PENDING

    def test_other_barber_same_slot_ok(self):
        appt = AppointmentFactory()
        other = AppointmentFactory(
            barber=BarberProfileFactory(),  # boshqa sartarosh
            date=appt.date,
            start_time=appt.start_time,
        )

        assert other.barber != appt.barber

    def test_different_time_same_day_ok(self):
        appt = AppointmentFactory()
        start = datetime.combine(appt.date, appt.start_time) + timedelta(minutes=30)

        other = AppointmentFactory(
            barber=appt.barber,
            date=appt.date,
            start_time=start.time(),
            end_time=(start + timedelta(minutes=30)).time(),
        )

        assert other.pk

    def test_history_related(self):
        appt = AppointmentFactory()
        history = AppointmentHistoryFactory(appointment=appt)

        assert list(appt.history.all()) == [history]


class TestAppointmentHistory:
    def test_fields(self):
        appt = AppointmentFactory(status=AppointmentStatus.CONFIRMED)
        user = UserFactory()
        history = AppointmentHistoryFactory(
            appointment=appt,
            old_status=AppointmentStatus.PENDING,
            new_status=AppointmentStatus.CONFIRMED,
            changed_by=user,
        )

        assert history.old_status == AppointmentStatus.PENDING
        assert history.new_status == AppointmentStatus.CONFIRMED
        assert history.changed_by == user

    def test_old_status_nullable(self):
        history = AppointmentHistoryFactory(old_status=None)

        assert history.old_status is None
        assert "-" in str(history)
