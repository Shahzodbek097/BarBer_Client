"""Bosqich 4: navbat amallari (confirm/reject/cancel/complete/no-show/propose)."""

from datetime import time, timedelta

import pytest
from django.utils import timezone

from apps.accounts.factories import UserFactory
from apps.accounts.models import User
from apps.barbers.factories import BarberProfileFactory
from apps.bookings.factories import AppointmentFactory
from apps.bookings.models import Appointment, AppointmentStatus
from apps.bookings.services import appointments as appt_service
from apps.bookings.services.exceptions import (
    AppointmentNotOwner,
    BookingValidationError,
    InvalidTransition,
    SlotUnavailable,
)
from apps.core.models import AuditLog
from apps.schedule.factories import WorkScheduleFactory

pytestmark = pytest.mark.django_db

PENDING, CONFIRMED = AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED
COMPLETED, NO_SHOW = AppointmentStatus.COMPLETED, AppointmentStatus.NO_SHOW
CANCELLED, REJECTED = AppointmentStatus.CANCELLED, AppointmentStatus.REJECTED


@pytest.fixture
def action_env():
    """Sartarosh + ertangi kun jadvali + PENDING navbat (10:00).

    Sartarosh faol (is_active_now) — qayta bandlov (ONLINE create) testida kerak.
    """
    barber = BarberProfileFactory(is_active_now=True)
    day = timezone.localdate() + timedelta(days=1)
    WorkScheduleFactory(
        barber=barber, weekday=day.weekday(), start_time=time(9, 0), end_time=time(18, 0)
    )
    appointment = AppointmentFactory(
        barber=barber, date=day, start_time=time(10, 0), end_time=time(10, 30)
    )
    return {"barber": barber, "day": day, "appointment": appointment}


def _barber_of(env):
    return env["appointment"].barber.user


def _stranger():
    return UserFactory(role=User.Role.CLIENT)


class TestConfirm:
    def test_barber_confirms(self, action_env):
        appointment = action_env["appointment"]

        result = appt_service.confirm(appointment, by=_barber_of(action_env))

        assert result.status == CONFIRMED
        history = appointment.history.get()
        assert history.old_status == PENDING and history.new_status == CONFIRMED
        assert AuditLog.objects.filter(action="appointment_confirmed").exists()

    def test_stranger_forbidden(self, action_env):
        with pytest.raises(AppointmentNotOwner):
            appt_service.confirm(action_env["appointment"], by=_stranger())

    def test_client_cannot_confirm(self, action_env):
        with pytest.raises(AppointmentNotOwner):
            appt_service.confirm(action_env["appointment"], by=action_env["appointment"].client)


class TestReject:
    def test_reject_with_reply(self, action_env):
        appointment = action_env["appointment"]

        result = appt_service.reject(appointment, by=_barber_of(action_env), reply="Bandman, uzr")

        assert result.status == REJECTED
        appointment.refresh_from_db()
        assert appointment.barber_reply == "Bandman, uzr"

    def test_stranger_forbidden(self, action_env):
        with pytest.raises(AppointmentNotOwner):
            appt_service.reject(action_env["appointment"], by=_stranger())


class TestCancel:
    def test_client_cancels_pending(self, action_env):
        appointment = action_env["appointment"]

        result = appt_service.cancel(appointment, by=appointment.client, comment="o'zgardi")

        assert result.status == CANCELLED
        assert appointment.history.get().comment == "o'zgardi"

    def test_barber_cancels_confirmed(self, action_env):
        appointment = action_env["appointment"]
        appt_service.confirm(appointment, by=_barber_of(action_env))

        result = appt_service.cancel(appointment, by=_barber_of(action_env))

        assert result.status == CANCELLED

    def test_cancelling_completed_invalid(self, action_env):
        appointment = action_env["appointment"]
        appt_service.confirm(appointment, by=_barber_of(action_env))
        appt_service.complete(appointment, by=_barber_of(action_env))

        with pytest.raises(InvalidTransition):
            appt_service.cancel(appointment, by=appointment.client)

    def test_stranger_forbidden(self, action_env):
        with pytest.raises(AppointmentNotOwner):
            appt_service.cancel(action_env["appointment"], by=_stranger())


class TestComplete:
    def test_barber_completes_confirmed(self, action_env):
        appointment = action_env["appointment"]
        appt_service.confirm(appointment, by=_barber_of(action_env))

        result = appt_service.complete(appointment, by=_barber_of(action_env))

        assert result.status == COMPLETED

    def test_cannot_complete_pending(self, action_env):
        with pytest.raises(InvalidTransition):
            appt_service.complete(action_env["appointment"], by=_barber_of(action_env))

    def test_stranger_forbidden(self, action_env):
        with pytest.raises(AppointmentNotOwner):
            appt_service.complete(action_env["appointment"], by=_stranger())


class TestNoShow:
    def test_barber_marks_no_show(self, action_env):
        appointment = action_env["appointment"]
        appt_service.confirm(appointment, by=_barber_of(action_env))

        result = appt_service.mark_no_show(appointment, by=_barber_of(action_env))

        assert result.status == NO_SHOW

    def test_cannot_no_show_pending(self, action_env):
        with pytest.raises(InvalidTransition):
            appt_service.mark_no_show(action_env["appointment"], by=_barber_of(action_env))


class TestProposeNewTime:
    def test_moves_and_keeps_pending(self, action_env):
        appointment = action_env["appointment"]

        result = appt_service.propose_new_time(
            appointment, by=_barber_of(action_env), day=action_env["day"], start_time=time(15, 0)
        )

        assert result.status == PENDING
        appointment.refresh_from_db()
        assert appointment.start_time == time(15, 0)
        assert appointment.end_time == time(15, 30)
        assert "taklif" in appointment.barber_reply.lower()
        history = appointment.history.get()
        assert "taklif" in history.comment

    def test_old_slot_becomes_free(self, action_env):
        appointment = action_env["appointment"]
        appt_service.propose_new_time(
            appointment, by=_barber_of(action_env), day=action_env["day"], start_time=time(15, 0)
        )

        # eski 10:00 slot yana bo'sh — yangi mijoz olishi mumkin
        fresh = AppointmentFactory(
            barber=action_env["barber"], date=action_env["day"], start_time=time(10, 0)
        )
        assert fresh.start_time == time(10, 0)

    def test_occupied_new_slot_rejected(self, action_env):
        AppointmentFactory(
            barber=action_env["barber"], date=action_env["day"], start_time=time(15, 0)
        )
        appointment = action_env["appointment"]

        with pytest.raises(SlotUnavailable):
            appt_service.propose_new_time(
                appointment,
                by=_barber_of(action_env),
                day=action_env["day"],
                start_time=time(15, 0),
            )

        appointment.refresh_from_db()
        assert appointment.start_time == time(10, 0)  # o'zgarmagan

    def test_past_time_rejected(self, action_env):
        today = timezone.localdate()

        with pytest.raises(BookingValidationError, match="O'tgan vaqt"):
            appt_service.propose_new_time(
                action_env["appointment"],
                by=_barber_of(action_env),
                day=today,
                start_time=time(0, 0),
            )

    def test_stranger_forbidden(self, action_env):
        with pytest.raises(AppointmentNotOwner):
            appt_service.propose_new_time(
                action_env["appointment"],
                by=_stranger(),
                day=action_env["day"],
                start_time=time(15, 0),
            )


class TestCancelFreesSlot:
    def test_cancelled_slot_rebookable(self, action_env):
        appointment = action_env["appointment"]
        appt_service.cancel(appointment, by=appointment.client)

        fresh = appt_service.create_appointment(
            client=UserFactory(role=User.Role.CLIENT),
            barber=action_env["barber"],
            service=appointment.service,
            day=action_env["day"],
            start_time=time(10, 0),
        )
        assert Appointment.objects.filter(pk=fresh.pk, status=PENDING).exists()
