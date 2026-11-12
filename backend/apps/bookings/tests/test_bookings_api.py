"""Bosqich 5: navbat API testlari (mijoz va sartarosh oqimlari).

Ruxsat matritsasi va IDOR izolyatsiyasi tekshiriladi: biznes mantiq
services qatlamida — view faqat chaqiradi.
"""

from datetime import time, timedelta

import pytest
from django.utils import timezone

from apps.accounts.factories import UserFactory
from apps.barbers.factories import BarberProfileFactory
from apps.bookings.factories import AppointmentFactory
from apps.bookings.models import AppointmentSource, AppointmentStatus
from apps.schedule.factories import WorkScheduleFactory
from apps.services.factories import ServiceFactory

pytestmark = pytest.mark.django_db


def _tomorrow():
    return timezone.localdate() + timedelta(days=1)


def _ready_barber(**kwargs):
    """Onlayn bandlovga tayyor sartarosh: tasdiqlangan, faol, jadval bor."""
    barber = BarberProfileFactory(is_active_now=True, **kwargs)
    WorkScheduleFactory(barber=barber, weekday=_tomorrow().weekday())
    return barber


class TestCreate:
    def test_client_creates_booking(self, api_client, make_auth_client):
        barber = _ready_barber()
        service = ServiceFactory(barber=barber)
        client_user = UserFactory()

        response = make_auth_client(client_user).post(
            "/api/v1/bookings/",
            {
                "barber": barber.id,
                "service": service.id,
                "date": _tomorrow().isoformat(),
                "start_time": "10:00:00",
                "note": "Iltimos, qisqa kesing",
            },
            format="json",
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == AppointmentStatus.PENDING
        assert data["start_time"] == "10:00:00"
        assert data["service_name"] == service.name
        assert data["client"] == client_user.id

    def test_anon_rejected(self, api_client):
        response = api_client.post("/api/v1/bookings/", {}, format="json")

        assert response.status_code == 401

    def test_barber_role_rejected(self, api_client, make_auth_client):
        barber = _ready_barber()

        response = make_auth_client(barber.user).post("/api/v1/bookings/", {}, format="json")

        assert response.status_code == 403

    def test_double_booking_conflict(self, api_client, make_auth_client):
        barber = _ready_barber()
        service = ServiceFactory(barber=barber)
        auth = make_auth_client(UserFactory())
        payload = {
            "barber": barber.id,
            "service": service.id,
            "date": _tomorrow().isoformat(),
            "start_time": "10:00:00",
        }

        assert auth.post("/api/v1/bookings/", payload, format="json").status_code == 201
        assert auth.post("/api/v1/bookings/", payload, format="json").status_code == 409

    def test_inactive_barber_rejected(self, api_client, make_auth_client):
        barber = BarberProfileFactory()  # is_active_now=False (model default)
        WorkScheduleFactory(barber=barber, weekday=_tomorrow().weekday())
        service = ServiceFactory(barber=barber)

        response = make_auth_client(UserFactory()).post(
            "/api/v1/bookings/",
            {
                "barber": barber.id,
                "service": service.id,
                "date": _tomorrow().isoformat(),
                "start_time": "10:00:00",
            },
            format="json",
        )

        assert response.status_code == 400


class TestMyList:
    def test_lists_only_own(self, api_client, make_auth_client):
        client_user = UserFactory()
        mine = AppointmentFactory(client=client_user)
        AppointmentFactory()  # boshqa mijozniki

        response = make_auth_client(client_user).get("/api/v1/bookings/my/")

        assert response.status_code == 200
        ids = [row["id"] for row in response.json()["results"]]
        assert ids == [mine.id]

    def test_status_filter(self, api_client, make_auth_client):
        client_user = UserFactory()
        pending = AppointmentFactory(client=client_user)
        AppointmentFactory(client=client_user, status=AppointmentStatus.CONFIRMED)

        response = make_auth_client(client_user).get("/api/v1/bookings/my/", {"status": "pending"})

        assert response.status_code == 200
        assert [row["id"] for row in response.json()["results"]] == [pending.id]

    def test_invalid_status_filter_rejected(self, api_client, make_auth_client):
        response = make_auth_client(UserFactory()).get("/api/v1/bookings/my/", {"status": "foo"})

        assert response.status_code == 400


class TestRetrieve:
    def test_client_participant_sees(self, api_client, make_auth_client):
        appt = AppointmentFactory()

        response = make_auth_client(appt.client).get(f"/api/v1/bookings/{appt.id}/")

        assert response.status_code == 200
        assert response.json()["id"] == appt.id

    def test_barber_participant_sees(self, api_client, make_auth_client):
        appt = AppointmentFactory()

        response = make_auth_client(appt.barber.user).get(f"/api/v1/bookings/{appt.id}/")

        assert response.status_code == 200
        assert response.json()["id"] == appt.id

    def test_stranger_gets_404(self, api_client, make_auth_client):
        appt = AppointmentFactory()

        response = make_auth_client(UserFactory()).get(f"/api/v1/bookings/{appt.id}/")

        assert response.status_code == 404


class TestCancel:
    def test_client_cancels_own(self, api_client, make_auth_client):
        appt = AppointmentFactory()

        response = make_auth_client(appt.client).post(f"/api/v1/bookings/{appt.id}/cancel/")

        assert response.status_code == 200
        assert response.json()["status"] == AppointmentStatus.CANCELLED

    def test_barber_can_cancel(self, api_client, make_auth_client):
        appt = AppointmentFactory()

        response = make_auth_client(appt.barber.user).post(f"/api/v1/bookings/{appt.id}/cancel/")

        assert response.status_code == 200
        assert response.json()["status"] == AppointmentStatus.CANCELLED

    def test_second_cancel_rejected(self, api_client, make_auth_client):
        appt = AppointmentFactory()
        auth = make_auth_client(appt.client)
        auth.post(f"/api/v1/bookings/{appt.id}/cancel/")

        response = auth.post(f"/api/v1/bookings/{appt.id}/cancel/")

        assert response.status_code == 409

    def test_stranger_gets_404(self, api_client, make_auth_client):
        appt = AppointmentFactory()

        response = make_auth_client(UserFactory()).post(f"/api/v1/bookings/{appt.id}/cancel/")

        assert response.status_code == 404


class TestReschedule:
    def test_client_moves_own_pending(self, api_client, make_auth_client):
        barber = _ready_barber()
        appt = AppointmentFactory(barber=barber, start_time=time(10, 0), end_time=time(10, 30))

        response = make_auth_client(appt.client).post(
            f"/api/v1/bookings/{appt.id}/reschedule/",
            {"date": _tomorrow().isoformat(), "start_time": "11:00:00"},
            format="json",
        )

        assert response.status_code == 200
        assert response.json()["start_time"] == "11:00:00"
        appt.refresh_from_db()
        assert appt.start_time == time(11, 0)

    def test_barber_cannot_reschedule(self, api_client, make_auth_client):
        barber = _ready_barber()
        appt = AppointmentFactory(barber=barber, start_time=time(10, 0), end_time=time(10, 30))

        response = make_auth_client(barber.user).post(
            f"/api/v1/bookings/{appt.id}/reschedule/",
            {"date": _tomorrow().isoformat(), "start_time": "11:00:00"},
            format="json",
        )

        assert response.status_code == 403

    def test_stranger_gets_404(self, api_client, make_auth_client):
        appt = AppointmentFactory()

        response = make_auth_client(UserFactory()).post(
            f"/api/v1/bookings/{appt.id}/reschedule/",
            {"date": _tomorrow().isoformat(), "start_time": "11:00:00"},
            format="json",
        )

        assert response.status_code == 404


class TestIncoming:
    def test_barber_lists_own(self, api_client, make_auth_client):
        barber = _ready_barber()
        appt = AppointmentFactory(barber=barber)
        AppointmentFactory()  # boshqa sartaroshniki

        response = make_auth_client(barber.user).get("/api/v1/bookings/incoming/")

        assert response.status_code == 200
        assert [row["id"] for row in response.json()["results"]] == [appt.id]

    def test_day_filter(self, api_client, make_auth_client):
        barber = _ready_barber()
        today = timezone.localdate()
        today_appt = AppointmentFactory(
            barber=barber, date=today, start_time=time(20, 0), end_time=time(20, 30)
        )
        AppointmentFactory(barber=barber)  # ertaga

        response = make_auth_client(barber.user).get(
            "/api/v1/bookings/incoming/", {"day": today.isoformat()}
        )

        assert [row["id"] for row in response.json()["results"]] == [today_appt.id]

    def test_status_filter(self, api_client, make_auth_client):
        barber = _ready_barber()
        pending = AppointmentFactory(barber=barber)
        AppointmentFactory(
            barber=barber,
            status=AppointmentStatus.CONFIRMED,
            start_time=time(11, 0),
            end_time=time(11, 30),
        )

        response = make_auth_client(barber.user).get(
            "/api/v1/bookings/incoming/", {"status": "pending"}
        )

        assert [row["id"] for row in response.json()["results"]] == [pending.id]

    def test_client_rejected(self, api_client, make_auth_client):
        response = make_auth_client(UserFactory()).get("/api/v1/bookings/incoming/")

        assert response.status_code == 403


class TestBarberActions:
    def test_confirm(self, api_client, make_auth_client):
        appt = AppointmentFactory()

        response = make_auth_client(appt.barber.user).post(f"/api/v1/bookings/{appt.id}/confirm/")

        assert response.status_code == 200
        assert response.json()["status"] == AppointmentStatus.CONFIRMED

    def test_confirm_by_client_rejected(self, api_client, make_auth_client):
        appt = AppointmentFactory()

        response = make_auth_client(appt.client).post(f"/api/v1/bookings/{appt.id}/confirm/")

        assert response.status_code == 403

    def test_reject_with_reply(self, api_client, make_auth_client):
        appt = AppointmentFactory()

        response = make_auth_client(appt.barber.user).post(
            f"/api/v1/bookings/{appt.id}/reject/", {"reply": "Bugun to'la"}, format="json"
        )

        assert response.status_code == 200
        assert response.json()["status"] == AppointmentStatus.REJECTED

    def test_propose_new_time(self, api_client, make_auth_client):
        barber = _ready_barber()
        appt = AppointmentFactory(barber=barber, start_time=time(10, 0), end_time=time(10, 30))

        response = make_auth_client(barber.user).post(
            f"/api/v1/bookings/{appt.id}/propose/",
            {"date": _tomorrow().isoformat(), "start_time": "11:00:00"},
            format="json",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == AppointmentStatus.PENDING
        assert data["start_time"] == "11:00:00"
        assert "taklif" in data["barber_reply"]

    def test_complete_after_confirm(self, api_client, make_auth_client):
        appt = AppointmentFactory(status=AppointmentStatus.CONFIRMED)

        response = make_auth_client(appt.barber.user).post(f"/api/v1/bookings/{appt.id}/complete/")

        assert response.status_code == 200
        assert response.json()["status"] == AppointmentStatus.COMPLETED

    def test_no_show_after_confirm(self, api_client, make_auth_client):
        appt = AppointmentFactory(status=AppointmentStatus.CONFIRMED)

        response = make_auth_client(appt.barber.user).post(f"/api/v1/bookings/{appt.id}/no-show/")

        assert response.status_code == 200
        assert response.json()["status"] == AppointmentStatus.NO_SHOW


class TestManualBooking:
    def test_barber_books_walkin_client(self, api_client, make_auth_client):
        barber = _ready_barber()
        service = ServiceFactory(barber=barber)
        walkin = UserFactory(phone="+998901119999")

        response = make_auth_client(barber.user).post(
            "/api/v1/bookings/manual/",
            {
                "client_phone": walkin.phone,
                "service": service.id,
                "date": _tomorrow().isoformat(),
                "start_time": "10:00:00",
            },
            format="json",
        )

        assert response.status_code == 201
        data = response.json()
        assert data["source"] == AppointmentSource.MANUAL
        assert data["client"] == walkin.id

    def test_unknown_phone_rejected(self, api_client, make_auth_client):
        barber = _ready_barber()
        service = ServiceFactory(barber=barber)

        response = make_auth_client(barber.user).post(
            "/api/v1/bookings/manual/",
            {
                "client_phone": "+998900000000",
                "service": service.id,
                "date": _tomorrow().isoformat(),
                "start_time": "10:00:00",
            },
            format="json",
        )

        assert response.status_code == 400

    def test_client_role_rejected(self, api_client, make_auth_client):
        response = make_auth_client(UserFactory()).post(
            "/api/v1/bookings/manual/", {}, format="json"
        )

        assert response.status_code == 403
