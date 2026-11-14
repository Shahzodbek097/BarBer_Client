"""Bosqich 8: E2E oqimlar (gate: 3 oqim) — API darajasida, haqiqiy auth.

Oqimlar:
- US-1: anon katalog → ro'yxatdan o'tish (OTP) → navbat → sartarosh tasdiqlaydi
- US-2: vaqt o'zgartirish → sartarosh taklifi → bekor qilish
- US-3: qo'lda yozish → bajarildi → sharh → kunlik hisobot (daromad)
"""

from datetime import timedelta

import pytest
from conftest import extract_code
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.factories import UserFactory
from apps.barbers.factories import BarberProfileFactory
from apps.bookings.models import Appointment, AppointmentStatus
from apps.schedule.factories import WorkScheduleFactory
from apps.services.factories import ServiceFactory

pytestmark = [pytest.mark.django_db, pytest.mark.e2e]

URL = "/api/v1"
CLIENT_PHONE = "+998955000001"
WALKIN_PHONE = "+998955000002"


def _auth_client(user):
    """Mustaqil klient (make_auth_client bitta APIClient'ni qayta ishlatadi —
    bir nechta rol oqimida kredensiallar ustma-ust tushmasligi kerak)."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    return client


def _tomorrow():
    return timezone.localdate() + timedelta(days=1)


def _today():
    return timezone.localdate()


def _ready_barber():
    """Onlayn bandlovga tayyor sartarosh: tasdiqlangan, faol, bugun va ertaga jadval."""
    barber = BarberProfileFactory(is_active_now=True)
    WorkScheduleFactory(barber=barber, weekday=_today().weekday())
    WorkScheduleFactory(barber=barber, weekday=_tomorrow().weekday())
    return barber


def _register_and_login(api_client, fake_sms, phone, full_name="E2E Mijoz"):
    """Ro'yxatdan o'tish → SMS kodi → verify-otp → Bearer bilan klient."""
    response = api_client.post(
        f"{URL}/auth/register/",
        {"phone": phone, "full_name": full_name, "role": "client"},
        format="json",
    )
    assert response.status_code == 201, response.json()
    code = extract_code(fake_sms[-1]["message"])
    verify = api_client.post(
        f"{URL}/auth/verify-otp/",
        {"phone": phone, "purpose": "registration", "code": code},
        format="json",
    )
    assert verify.status_code == 200, verify.json()
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {verify.json()['access']}")
    return api_client


class TestUS1AnonToBooking:
    def test_anon_browse_register_book_confirm(self, api_client, fake_sms):
        barber = _ready_barber()
        service = ServiceFactory(barber=barber)

        # 1) anon katalog: sartarosh, xizmatlar, slotlar — ochiq
        barbers = api_client.get(f"{URL}/catalog/barbers/").json()
        assert any(row["id"] == barber.id for row in barbers["results"])

        services = api_client.get(f"{URL}/catalog/barbers/{barber.id}/services/").json()
        assert any(row["id"] == service.id for row in services)

        slots = api_client.get(
            f"{URL}/catalog/barbers/{barber.id}/slots/",
            {"service_id": service.id, "day": _tomorrow().isoformat()},
        ).json()
        assert any(slot["start"].startswith("10:00") for slot in slots)

        # 2) ro'yxatdan o'tish + OTP tasdiqlash
        client_api = _register_and_login(api_client, fake_sms, CLIENT_PHONE)

        # 3) navbat yaratish
        created = client_api.post(
            f"{URL}/bookings/",
            {
                "barber": barber.id,
                "service": service.id,
                "date": _tomorrow().isoformat(),
                "start_time": "10:00:00",
                "note": "Iltimos, soqolni qisqa oling",
            },
            format="json",
        )
        assert created.status_code == 201, created.json()
        appointment_id = created.json()["id"]
        assert created.json()["status"] == AppointmentStatus.PENDING

        # 4) sartarosh kiruvchi ro'yxatida ko'rinadi va tasdiqlaydi
        barber_api = _auth_client(barber.user)
        incoming = barber_api.get(f"{URL}/bookings/incoming/").json()
        assert any(row["id"] == appointment_id for row in incoming["results"])

        confirmed = barber_api.post(f"{URL}/bookings/{appointment_id}/confirm/")
        assert confirmed.status_code == 200
        assert confirmed.json()["status"] == AppointmentStatus.CONFIRMED

        # 5) mijoz holatni va xabarnomasini ko'radi
        assert client_api.get(f"{URL}/bookings/{appointment_id}/").json()["status"] == "confirmed"
        notes = client_api.get(f"{URL}/notifications/").json()
        assert any(row["type"] == "booking_confirmed" for row in notes["results"])


class TestUS2ChangeProposeCancel:
    def test_reschedule_propose_then_cancel(self, api_client, fake_sms):
        barber = _ready_barber()
        service = ServiceFactory(barber=barber)
        client_api = _register_and_login(api_client, fake_sms, CLIENT_PHONE)
        barber_api = _auth_client(barber.user)

        # mijoz navbat yaratadi
        appointment_id = client_api.post(
            f"{URL}/bookings/",
            {
                "barber": barber.id,
                "service": service.id,
                "date": _tomorrow().isoformat(),
                "start_time": "10:00:00",
            },
            format="json",
        ).json()["id"]

        # 1) mijoz o'z navbatini boshqa bo'sh vaqtga ko'chiradi
        moved = client_api.post(
            f"{URL}/bookings/{appointment_id}/reschedule/",
            {"date": _tomorrow().isoformat(), "start_time": "12:00:00"},
            format="json",
        )
        assert moved.status_code == 200, moved.json()
        assert moved.json()["start_time"] == "12:00:00"

        # 2) sartarosh boshqa vaqt taklif qiladi (PENDING qoladi)
        proposed = barber_api.post(
            f"{URL}/bookings/{appointment_id}/propose/",
            {"date": _tomorrow().isoformat(), "start_time": "15:00:00"},
            format="json",
        )
        assert proposed.status_code == 200, proposed.json()
        data = proposed.json()
        assert data["status"] == AppointmentStatus.PENDING
        assert data["start_time"] == "15:00:00"
        assert "taklif" in data["barber_reply"].lower()

        # 3) mijoz qabul qilmadi — bekor qiladi; tarix saqlanadi
        cancelled = client_api.post(f"{URL}/bookings/{appointment_id}/cancel/")
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == AppointmentStatus.CANCELLED

        appointment = Appointment.objects.get(pk=appointment_id)
        assert appointment.history.count() >= 3  # ko'chirish + taklif + bekor


class TestUS3ManualCompleteReviewReport:
    def test_walkin_complete_review_and_report(self, api_client):
        barber = _ready_barber()
        service = ServiceFactory(barber=barber)
        walkin = UserFactory(phone=WALKIN_PHONE)
        barber_api = _auth_client(barber.user)

        # 1) orxonadagi mijozga qo'lda navbat (ertaga — bugungi vaqt o'tib bo'lishi mumkin)
        manual = barber_api.post(
            f"{URL}/bookings/manual/",
            {
                "client_phone": WALKIN_PHONE,
                "service": service.id,
                "date": _tomorrow().isoformat(),
                "start_time": "10:00:00",
            },
            format="json",
        )
        assert manual.status_code == 201, manual.json()
        appointment_id = manual.json()["id"]
        assert manual.json()["source"] == "manual"

        # 2) bajarildi
        assert barber_api.post(f"{URL}/bookings/{appointment_id}/confirm/").status_code == 200
        completed = barber_api.post(f"{URL}/bookings/{appointment_id}/complete/")
        assert completed.status_code == 200
        assert completed.json()["status"] == AppointmentStatus.COMPLETED

        # 3) mijoz sharh yozadi → reyting yangilanadi
        client_api = _auth_client(walkin)
        review = client_api.post(
            f"{URL}/reviews/",
            {"appointment": appointment_id, "rating": 5, "comment": "Zo'r ish!"},
            format="json",
        )
        assert review.status_code == 201, review.json()

        catalog_row = next(
            row
            for row in api_client.get(f"{URL}/catalog/barbers/").json()["results"]
            if row["id"] == barber.id
        )
        assert float(catalog_row["rating_avg"]) == 5.0
        assert catalog_row["rating_count"] == 1

        # 4) sartarosh kunlik hisobotida daromad ko'rinadi
        report = barber_api.get(f"{URL}/barber/report/", {"day": _tomorrow().isoformat()}).json()
        assert report["totals"]["by_status"]["completed"] == 1
        assert float(report["totals"]["revenue"]) == 50000.0

        # 5) sharhlar ochiq ko'rinadi
        reviews = api_client.get(f"{URL}/reviews/barber/{barber.id}/").json()
        assert len(reviews) == 1 and reviews[0]["rating"] == 5
