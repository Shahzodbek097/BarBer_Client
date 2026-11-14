"""Bosqich 8: IDOR testlar to'plami (object-level ruxsatlar).

Har bir test bitta savol beradi: "B foydalanuvchi A obyektiga
kirishi / amallarini bajarishi mumkinmi?" — javob har doim
404 (ob'ekt mavjudligi ham yashiriladi) yoki 403 (rol yetarli emas),
bo'lmasa 400 (faqat xatoni tushunish mumkin, ob'ekt haqida yo'q).
200/201/204/haqiqiy ma'lumot qaytishi = IDOR xatosi.
"""

from datetime import time, timedelta

import pytest
from django.utils import timezone

from apps.accounts.factories import UserFactory
from apps.accounts.models import User
from apps.barbers.factories import BarberProfileFactory
from apps.bookings.factories import AppointmentFactory
from apps.bookings.models import AppointmentStatus
from apps.notifications.factories import NotificationFactory
from apps.salons.factories import SalonFactory
from apps.schedule.factories import DayOffFactory, ScheduleBreakFactory, WorkScheduleFactory
from apps.services.factories import ServiceFactory
from apps.telegram.models import TelegramChat

pytestmark = [pytest.mark.django_db, pytest.mark.integration]

URL = "/api/v1"


def _tomorrow():
    return timezone.localdate() + timedelta(days=1)


class TestBookingObjectIsolation:
    """Mijoz faqat O'Z navbatini ko'radi/o'zgartiradi."""

    def _pair(self):
        """Bir sartaroshning ikki mijozga tegishli navbatlari."""
        barber = BarberProfileFactory()
        client_a = UserFactory(full_name="A Mijoz")
        client_b = UserFactory(full_name="B Mijoz")
        appt_a = AppointmentFactory(client=client_a, barber=barber, start_time=time(10, 0))
        appt_b = AppointmentFactory(client=client_b, barber=barber, start_time=time(11, 0))
        return appt_a, appt_b

    def test_foreign_retrieve_404(self, api_client, make_auth_client):
        appt_a, appt_b = self._pair()
        foreign = make_auth_client(appt_b.client)

        response = foreign.get(f"{URL}/bookings/{appt_a.pk}/")

        assert response.status_code == 404

    def test_foreign_cancel_404_and_unchanged(self, api_client, make_auth_client):
        appt_a, appt_b = self._pair()
        foreign = make_auth_client(appt_b.client)

        assert foreign.post(f"{URL}/bookings/{appt_a.pk}/cancel/").status_code == 404

        appt_a.refresh_from_db()
        assert appt_a.status == AppointmentStatus.PENDING

    def test_foreign_reschedule_404_and_unchanged(self, api_client, make_auth_client):
        appt_a, appt_b = self._pair()
        foreign = make_auth_client(appt_b.client)

        response = foreign.post(
            f"{URL}/bookings/{appt_a.pk}/reschedule/",
            {"date": _tomorrow().isoformat(), "start_time": "16:00:00"},
            format="json",
        )

        assert response.status_code == 404
        appt_a.refresh_from_db()
        assert appt_a.start_time == time(10, 0)

    def test_my_list_hides_foreign(self, api_client, make_auth_client):
        appt_a, appt_b = self._pair()
        foreign = make_auth_client(appt_b.client)

        ids = [row["id"] for row in foreign.get(f"{URL}/bookings/my/").json()["results"]]

        assert appt_a.pk not in ids

    def test_another_client_appointment_visible_in_retrieve_pairing(
        self, api_client, make_auth_client
    ):
        """Ijodkor o'z navbatini ko'radi (ijobiy nazorat)."""
        appt_a, _ = self._pair()
        owner = make_auth_client(appt_a.client)

        response = owner.get(f"{URL}/bookings/{appt_a.pk}/")

        assert response.status_code == 200
        assert response.json()["id"] == appt_a.pk


class TestBarberActionIsolation:
    """Sartarosh faqat O'Z navbatlariga amallar bajara oladi."""

    def _setup(self):
        owner = BarberProfileFactory()
        appt = AppointmentFactory(barber=owner)  # ertaga 10:00
        intruder = BarberProfileFactory()
        return appt, intruder

    def _assert_blocked(self, make_auth_client, appt, intruder, action, payload=None):
        response = make_auth_client(intruder.user).post(
            f"{URL}/bookings/{appt.pk}/{action}/", payload or {}, format="json"
        )
        assert response.status_code == 404, f"{action}: {response.status_code}"
        appt.refresh_from_db()
        assert appt.status == AppointmentStatus.PENDING
        return response

    def test_confirm(self, make_auth_client):
        appt, intruder = self._setup()
        self._assert_blocked(make_auth_client, appt, intruder, "confirm")

    def test_reject(self, make_auth_client):
        appt, intruder = self._setup()
        self._assert_blocked(make_auth_client, appt, intruder, "reject", {"reply": "yo'q"})

    def test_propose(self, make_auth_client):
        appt, intruder = self._setup()
        self._assert_blocked(
            make_auth_client,
            appt,
            intruder,
            "propose",
            {"date": _tomorrow().isoformat(), "start_time": "16:00:00"},
        )
        assert appt.barber_reply == ""  # taklif yozuvi ham sizib chiqmagan

    def test_complete(self, make_auth_client):
        appt, intruder = self._setup()
        self._assert_blocked(make_auth_client, appt, intruder, "complete")

    def test_no_show(self, make_auth_client):
        appt, intruder = self._setup()
        self._assert_blocked(make_auth_client, appt, intruder, "no-show")

    def test_cancel_by_foreign_barber(self, make_auth_client):
        appt, intruder = self._setup()
        self._assert_blocked(make_auth_client, appt, intruder, "cancel")

    def test_incoming_hides_other_barbers(self, api_client, make_auth_client):
        appt, intruder = self._setup()

        ids = [
            row["id"]
            for row in make_auth_client(intruder.user)
            .get(f"{URL}/bookings/incoming/")
            .json()["results"]
        ]

        assert appt.pk not in ids


class TestNotificationIsolation:
    def _pair(self):
        user_a = UserFactory()
        user_b = UserFactory()
        note_a = NotificationFactory(recipient=user_a)
        return user_a, user_b, note_a

    def test_foreign_detail_404(self, api_client, make_auth_client):
        _, user_b, note_a = self._pair()

        assert make_auth_client(user_b).get(f"{URL}/notifications/{note_a.pk}/").status_code == 404

    def test_foreign_read_404_and_unchanged(self, api_client, make_auth_client):
        _, user_b, note_a = self._pair()

        assert (
            make_auth_client(user_b).post(f"{URL}/notifications/{note_a.pk}/read/").status_code
            == 404
        )
        note_a.refresh_from_db()
        assert note_a.is_read is False

    def test_list_excludes_foreign(self, api_client, make_auth_client):
        _, user_b, note_a = self._pair()
        NotificationFactory(recipient=user_b)

        ids = [
            row["id"]
            for row in make_auth_client(user_b).get(f"{URL}/notifications/").json()["results"]
        ]

        assert note_a.pk not in ids

    def test_unread_count_own_only(self, api_client, make_auth_client):
        _, user_b, _ = self._pair()
        NotificationFactory(recipient=user_b)

        data = make_auth_client(user_b).get(f"{URL}/notifications/unread-count/").json()

        assert data["unread"] == 1


class TestBarberCabinetIsolation:
    def _pair(self):
        owner = BarberProfileFactory()
        intruder = BarberProfileFactory()
        return owner, intruder

    def test_foreign_service_detail_404(self, api_client, make_auth_client):
        owner, intruder = self._pair()
        service = ServiceFactory(barber=owner)

        response = make_auth_client(intruder.user).get(f"{URL}/barber/services/{service.pk}/")

        assert response.status_code == 404

    def test_foreign_service_patch_404_and_unchanged(self, api_client, make_auth_client):
        owner, intruder = self._pair()
        service = ServiceFactory(barber=owner)

        response = make_auth_client(intruder.user).patch(
            f"{URL}/barber/services/{service.pk}/", {"name": "Hujum"}, format="json"
        )

        assert response.status_code == 404
        service.refresh_from_db()
        assert service.name != "Hujum"

    def test_foreign_service_delete_404_and_active(self, api_client, make_auth_client):
        owner, intruder = self._pair()
        service = ServiceFactory(barber=owner)

        assert (
            make_auth_client(intruder.user)
            .delete(f"{URL}/barber/services/{service.pk}/")
            .status_code
            == 404
        )
        service.refresh_from_db()
        assert service.is_active is True

    def test_services_list_own_only(self, api_client, make_auth_client):
        owner, intruder = self._pair()
        mine = ServiceFactory(barber=intruder)
        ServiceFactory(barber=owner)

        ids = [
            row["id"]
            for row in make_auth_client(intruder.user)
            .get(f"{URL}/barber/services/")
            .json()["results"]
        ]

        assert ids == [mine.pk]

    def test_foreign_break_delete_rejected(self, api_client, make_auth_client):
        owner, intruder = self._pair()
        schedule = WorkScheduleFactory(barber=owner)
        brk = ScheduleBreakFactory(schedule=schedule)

        response = make_auth_client(intruder.user).delete(f"{URL}/barber/schedule/breaks/{brk.pk}/")

        assert response.status_code == 400  # "Tanaffus topilmadi." — mavjudligi yashirilmaydi

    def test_breaks_list_own_only(self, api_client, make_auth_client):
        owner, intruder = self._pair()
        ScheduleBreakFactory(schedule=WorkScheduleFactory(barber=owner))

        data = make_auth_client(intruder.user).get(f"{URL}/barber/schedule/breaks/").json()

        assert data == []

    def test_foreign_dayoff_delete_rejected(self, api_client, make_auth_client):
        owner, intruder = self._pair()
        day_off = DayOffFactory(barber=owner)

        response = make_auth_client(intruder.user).delete(f"{URL}/barber/day-offs/{day_off.pk}/")

        assert response.status_code == 400

    def test_dayoffs_list_own_only(self, api_client, make_auth_client):
        owner, intruder = self._pair()
        DayOffFactory(barber=owner)

        data = make_auth_client(intruder.user).get(f"{URL}/barber/day-offs/").json()

        assert data == []


class TestSalonIsolation:
    def test_profile_returns_own_salon(self, api_client, make_auth_client):
        salon_a = SalonFactory(name="A Saloni")
        SalonFactory(name="B Saloni")
        owner_b = SalonFactory(name="C Saloni").owner

        data = make_auth_client(salon_a.owner).get(f"{URL}/salon/profile/").json()

        assert data["name"] == "A Saloni"
        assert data["name"] != make_auth_client(owner_b).get(f"{URL}/salon/profile/").json()["name"]

    def test_barbers_of_own_salon_only(self, api_client, make_auth_client):
        from apps.barbers.factories import BarberProfileFactory

        salon_a = SalonFactory()
        salon_b = SalonFactory()
        mine = BarberProfileFactory(salon=salon_a)
        BarberProfileFactory(salon=salon_b)

        ids = [
            row["id"] for row in make_auth_client(salon_a.owner).get(f"{URL}/salon/barbers/").json()
        ]

        assert ids == [mine.pk]


class TestAdminIsolation:
    @pytest.mark.parametrize(
        ("role", "url"),
        [
            (User.Role.CLIENT, "/admin/stats/"),
            (User.Role.BARBER, "/admin/stats/"),
            (User.Role.SALON_ADMIN, "/admin/stats/"),
            (User.Role.CLIENT, "/admin/salons/"),
            (User.Role.BARBER, "/admin/salons/"),
            (User.Role.SALON_ADMIN, "/admin/salons/"),
            (User.Role.CLIENT, "/admin/report/"),
            (User.Role.BARBER, "/admin/report/"),
            (User.Role.SALON_ADMIN, "/admin/report/"),
            (User.Role.CLIENT, "/admin/salons/"),
        ],
    )
    def test_non_admin_403(self, api_client, make_auth_client, role, url):
        user = UserFactory(role=role)

        assert make_auth_client(user).get(f"{URL}{url}").status_code == 403


class TestTelegramStatusIsolation:
    def test_status_does_not_leak_foreign_chat(self, api_client, make_auth_client):
        user_a = UserFactory()
        TelegramChat.objects.create(user=user_a, chat_id=111, username="a")
        user_b = UserFactory()

        data = make_auth_client(user_b).get(f"{URL}/telegram/link/").json()

        assert data["linked"] is False
        assert "chat_id" not in data


@pytest.mark.parametrize(
    "url",
    [
        "/bookings/my/",
        "/bookings/incoming/",
        "/notifications/",
        "/barber/profile/",
        "/barber/services/",
        "/barber/report/",
        "/salon/profile/",
        "/salon/report/",
        "/admin/stats/",
        "/admin/report/",
        "/telegram/link/",
        "/auth/me/",
    ],
)
def test_unauthenticated_401(api_client, url):
    """Shaxsiy endpointlar autentifikatsiyasiz mazmunsiz 401 qaytaradi."""
    assert api_client.get(f"{URL}{url}").status_code == 401
