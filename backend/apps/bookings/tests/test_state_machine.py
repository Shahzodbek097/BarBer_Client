"""Bosqich 4: navbat holat mashinasi testlari (matritsa + transition)."""

import pytest

from apps.barbers.factories import BarberProfileFactory
from apps.bookings.factories import AppointmentFactory
from apps.bookings.models import AppointmentStatus
from apps.bookings.services.exceptions import InvalidTransition
from apps.bookings.services.state_machine import TRANSITIONS, can_transition, transition

pytestmark = pytest.mark.django_db

P, C, CO, R, X, N = (  # noqa: E741
    AppointmentStatus.PENDING,
    AppointmentStatus.CONFIRMED,
    AppointmentStatus.COMPLETED,
    AppointmentStatus.REJECTED,
    AppointmentStatus.CANCELLED,
    AppointmentStatus.NO_SHOW,
)

VALID = {
    (P, C),
    (P, R),
    (P, X),
    (C, CO),
    (C, N),
    (C, X),
}
ALL_STATUSES = [P, C, CO, R, X, N]


class TestTransitionMatrix:
    @pytest.mark.parametrize("old", ALL_STATUSES)
    def test_valid_transitions(self, old):
        expected = {
            P: {C, R, X},
            C: {CO, N, X},
            CO: set(),
            R: set(),
            X: set(),
            N: set(),
        }[old]

        assert {s for s in ALL_STATUSES if can_transition(old, s)} == expected

    def test_transition_map_matches_valid_set(self):
        assert {(old, new) for old, news in TRANSITIONS.items() for new in news} == VALID


class TestTransitionFunction:
    @pytest.fixture
    def appointment(self):
        barber = BarberProfileFactory()
        return AppointmentFactory(barber=barber, status=P)

    def test_confirms_and_writes_history(self, appointment):
        barber_user = appointment.barber.user

        result = transition(appointment, C, changed_by=barber_user, comment="ok")

        assert result.status == C
        appointment.refresh_from_db()
        assert appointment.status == C
        history = appointment.history.get()
        assert history.old_status == P and history.new_status == C
        assert history.changed_by == barber_user

    @pytest.mark.parametrize(("old", "new"), [(CO, P), (R, C), (X, C), (P, CO), (CO, N)])
    def test_invalid_transition_raises(self, appointment, old, new):
        appointment.status = old
        appointment.save(update_fields=("status",))
        before_history = appointment.history.count()

        with pytest.raises(InvalidTransition):
            transition(appointment, new)

        appointment.refresh_from_db()
        assert appointment.status == old  # bazada o'zgarmagan
        assert appointment.history.count() == before_history

    def test_same_status_rejected(self, appointment):
        with pytest.raises(InvalidTransition):
            transition(appointment, P)

    @pytest.mark.parametrize("old", [CO, R, X, N])
    def test_terminal_states_reject_any_move(self, appointment, old):
        appointment.status = old
        appointment.save(update_fields=("status",))

        for new in ALL_STATUSES:
            if new != old:
                with pytest.raises(InvalidTransition):
                    transition(appointment, new)


class TestFullLifecycle:
    def test_pending_to_completed_chain(self):
        barber = BarberProfileFactory()
        appointment = AppointmentFactory(barber=barber, status=P)

        transition(appointment, C)
        transition(appointment, CO)

        assert appointment.history.count() == 2
