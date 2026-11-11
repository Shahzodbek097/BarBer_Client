"""Bosqich 4: create_appointment validatsiya va integratsiya testlari."""

from datetime import time, timedelta
from types import SimpleNamespace

import pytest
from django.utils import timezone

from apps.accounts.factories import UserFactory
from apps.accounts.models import User
from apps.barbers.factories import BarberProfileFactory
from apps.barbers.models import BarberStatus
from apps.bookings.factories import AppointmentFactory
from apps.bookings.models import AppointmentStatus
from apps.bookings.services import appointments as appt_service
from apps.bookings.services.exceptions import BookingValidationError, SlotUnavailable
from apps.core.models import AuditLog
from apps.salons.factories import SalonFactory
from apps.schedule.factories import ScheduleBreakFactory, WorkScheduleFactory
from apps.services.factories import ServiceFactory
from apps.services.models import ServiceOwner

pytestmark = pytest.mark.django_db


@pytest.fixture
def booking_env():
    """Tayyor sartarosh + ertangi kun jadvali + 30 daqiqalik xizmat."""
    barber = BarberProfileFactory(is_active_now=True)
    day = timezone.localdate() + timedelta(days=1)
    WorkScheduleFactory(
        barber=barber, weekday=day.weekday(), start_time=time(9, 0), end_time=time(18, 0)
    )
    service = ServiceFactory(barber=barber, duration_min=30)
    client = UserFactory(role=User.Role.CLIENT)
    return SimpleNamespace(barber=barber, day=day, service=service, client=client)


def _create(env, start_time=time(10, 0), **kwargs):
    return appt_service.create_appointment(
        client=env.client,
        barber=env.barber,
        service=env.service,
        day=env.day,
        start_time=start_time,
        **kwargs,
    )


class TestCreateSuccess:
    def test_creates_with_frozen_price_and_history(self, booking_env):
        appointment = _create(booking_env, note="Soqol qisqaroq bo'lsin")

        assert appointment.status == AppointmentStatus.PENDING
        assert appointment.end_time == time(10, 30)
        assert appointment.price == booking_env.service.price
        assert appointment.salon == booking_env.barber.salon
        assert appointment.client_note == "Soqol qisqaroq bo'lsin"
        assert appointment.source == "online"

        history = appointment.history.get()
        assert history.old_status is None
        assert history.new_status == AppointmentStatus.PENDING
        assert history.changed_by == booking_env.client

        assert AuditLog.objects.filter(
            action="appointment_created", object_id=str(appointment.pk)
        ).exists()

    def test_price_snapshot_ignores_later_change(self, booking_env):
        appointment = _create(booking_env)

        booking_env.service.price = 999999
        booking_env.service.save(update_fields=("price",))

        appointment.refresh_from_db()
        assert appointment.price != booking_env.service.price

    def test_end_time_matches_duration(self, booking_env):
        booking_env.service.duration_min = 45
        booking_env.service.save(update_fields=("duration_min",))

        appointment = _create(booking_env, start_time=time(10, 0))

        assert appointment.end_time == time(10, 45)

    def test_manual_source_skips_active_now(self, booking_env):
        booking_env.barber.is_active_now = False
        booking_env.barber.save(update_fields=("is_active_now",))

        appointment = _create(booking_env, source="manual")

        assert appointment.source == "manual"


class TestCreateValidations:
    def test_barber_not_approved_rejected(self):
        barber = BarberProfileFactory(status=BarberStatus.PENDING, is_active_now=True)
        day = timezone.localdate() + timedelta(days=1)
        WorkScheduleFactory(barber=barber, weekday=day.weekday())
        service = ServiceFactory(barber=barber)

        with pytest.raises(BookingValidationError, match="tasdiqlanmagan"):
            appt_service.create_appointment(
                client=UserFactory(),
                barber=barber,
                service=service,
                day=day,
                start_time=time(10, 0),
            )

    def test_barber_inactive_now_rejected(self, booking_env):
        booking_env.barber.is_active_now = False
        booking_env.barber.save(update_fields=("is_active_now",))

        with pytest.raises(BookingValidationError, match="nofaol"):
            _create(booking_env)

    def test_deleted_barber_rejected(self, booking_env):
        booking_env.barber.is_deleted = True
        booking_env.barber.save(update_fields=("is_deleted",))

        with pytest.raises(BookingValidationError, match="topilmadi"):
            _create(booking_env)

    def test_inactive_service_rejected(self, booking_env):
        booking_env.service.is_active = False
        booking_env.service.save(update_fields=("is_active",))

        with pytest.raises(BookingValidationError, match="nofaol"):
            _create(booking_env)

    def test_foreign_barber_service_rejected(self, booking_env):
        foreign_service = ServiceFactory(duration_min=30)  # boshqa sartarosh

        with pytest.raises(BookingValidationError, match="tegishli emas"):
            appt_service.create_appointment(
                client=booking_env.client,
                barber=booking_env.barber,
                service=foreign_service,
                day=booking_env.day,
                start_time=time(10, 0),
            )

    def test_salon_service_from_other_salon_rejected(self, booking_env):
        other = ServiceFactory(
            owner_type=ServiceOwner.SALON,
            barber=None,
            salon=SalonFactory(),  # boshqa salon
        )

        with pytest.raises(BookingValidationError, match="tegishli emas"):
            appt_service.create_appointment(
                client=booking_env.client,
                barber=booking_env.barber,
                service=other,
                day=booking_env.day,
                start_time=time(10, 0),
            )

    def test_salon_service_matching_salon_accepted(self, booking_env):
        service = ServiceFactory(
            owner_type=ServiceOwner.SALON, barber=None, salon=booking_env.barber.salon
        )

        appointment = appt_service.create_appointment(
            client=booking_env.client,
            barber=booking_env.barber,
            service=service,
            day=booking_env.day,
            start_time=time(10, 0),
        )

        assert appointment.service == service

    def test_past_date_rejected(self, booking_env):
        past = timezone.localdate() - timedelta(days=1)
        WorkScheduleFactory(barber=booking_env.barber, weekday=past.weekday())

        with pytest.raises(BookingValidationError, match="O'tgan sana"):
            appt_service.create_appointment(
                client=booking_env.client,
                barber=booking_env.barber,
                service=booking_env.service,
                day=past,
                start_time=time(10, 0),
            )

    def test_past_time_today_rejected(self, booking_env):
        today = timezone.localdate()
        WorkScheduleFactory(barber=booking_env.barber, weekday=today.weekday())

        with pytest.raises(BookingValidationError, match="O'tgan vaqt"):
            appt_service.create_appointment(
                client=booking_env.client,
                barber=booking_env.barber,
                service=booking_env.service,
                day=today,
                start_time=time(0, 0),
            )


class TestCreateSlotRules:
    def test_taken_slot_rejected(self, booking_env):
        AppointmentFactory(barber=booking_env.barber, date=booking_env.day, start_time=time(10, 0))

        with pytest.raises(SlotUnavailable):
            _create(booking_env, start_time=time(10, 0))

    def test_overlapping_slot_rejected(self, booking_env):
        AppointmentFactory(barber=booking_env.barber, date=booking_env.day, start_time=time(10, 0))

        with pytest.raises(SlotUnavailable):
            _create(booking_env, start_time=time(10, 15))

    def test_break_slot_rejected(self, booking_env):
        schedule = booking_env.barber.work_schedules.get(weekday=booking_env.day.weekday())
        ScheduleBreakFactory(schedule=schedule, start_time=time(12, 0), end_time=time(13, 0))

        with pytest.raises(SlotUnavailable):
            _create(booking_env, start_time=time(12, 30))

    @pytest.mark.parametrize("status", ["cancelled", "rejected"])
    def test_cancelled_and_rejected_do_not_block(self, booking_env, status):
        AppointmentFactory(
            barber=booking_env.barber, date=booking_env.day, start_time=time(10, 0), status=status
        )

        appointment = _create(booking_env, start_time=time(10, 0))

        assert appointment.status == AppointmentStatus.PENDING
