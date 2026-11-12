"""Bosqich 5: sartarosh kabineti API testlari (profil, xizmat, jadval, holat)."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.factories import UserFactory
from apps.accounts.models import User
from apps.barbers.factories import BarberProfileFactory
from apps.schedule.factories import DayOffFactory, ScheduleBreakFactory, WorkScheduleFactory
from apps.schedule.models import Weekday
from apps.services.factories import ServiceCategoryFactory, ServiceFactory

pytestmark = pytest.mark.django_db


class TestProfile:
    def test_get_without_profile_404(self, api_client, make_auth_client):
        barber_user = UserFactory(role=User.Role.BARBER)

        response = make_auth_client(barber_user).get("/api/v1/barber/profile/")

        assert response.status_code == 404

    def test_create(self, api_client, make_auth_client):
        barber_user = UserFactory(role=User.Role.BARBER)
        auth = make_auth_client(barber_user)

        response = auth.post(
            "/api/v1/barber/profile/",
            {"bio": "Salom, men sartaroshman", "experience_years": 5},
            format="json",
        )

        assert response.status_code == 201
        assert response.json()["bio"] == "Salom, men sartaroshman"

        # ikkinchi marta yaratish mumkin emas
        assert auth.post("/api/v1/barber/profile/", {}, format="json").status_code == 400

    def test_get_existing(self, api_client, make_auth_client):
        barber = BarberProfileFactory()

        response = make_auth_client(barber.user).get("/api/v1/barber/profile/")

        assert response.status_code == 200
        assert response.json()["id"] == barber.id

    def test_patch(self, api_client, make_auth_client):
        barber = BarberProfileFactory()
        category = ServiceCategoryFactory()

        response = make_auth_client(barber.user).patch(
            "/api/v1/barber/profile/",
            {
                "bio": "Yangi bio",
                "portfolio_images": ["/media/a.jpg"],
                "specialties": [category.id],
            },
            format="json",
        )

        assert response.status_code == 200
        barber.refresh_from_db()
        assert barber.bio == "Yangi bio"
        assert list(barber.specialties.values_list("id", flat=True)) == [category.id]

    def test_client_role_rejected(self, api_client, make_auth_client):
        response = make_auth_client(UserFactory()).get("/api/v1/barber/profile/")

        assert response.status_code == 403


class TestServices:
    def test_create(self, api_client, make_auth_client):
        barber = BarberProfileFactory()
        category = ServiceCategoryFactory()

        response = make_auth_client(barber.user).post(
            "/api/v1/barber/services/",
            {"category": category.id, "name": "Feyd", "duration_min": 20, "price": "30000.00"},
            format="json",
        )

        assert response.status_code == 201
        assert response.json()["is_active"] is True
        assert response.json()["name"] == "Feyd"

    def test_list_isolated(self, api_client, make_auth_client):
        barber = BarberProfileFactory()
        own = ServiceFactory(barber=barber)
        ServiceFactory()  # boshqa sartaroshniki

        response = make_auth_client(barber.user).get("/api/v1/barber/services/")

        assert response.status_code == 200
        assert [row["id"] for row in response.json()["results"]] == [own.id]

    def test_patch(self, api_client, make_auth_client):
        barber = BarberProfileFactory()
        service = ServiceFactory(barber=barber)

        response = make_auth_client(barber.user).patch(
            f"/api/v1/barber/services/{service.id}/", {"price": "40000.00"}, format="json"
        )

        assert response.status_code == 200
        service.refresh_from_db()
        assert str(service.price) == "40000.00"

    def test_soft_delete(self, api_client, make_auth_client):
        barber = BarberProfileFactory()
        service = ServiceFactory(barber=barber)

        response = make_auth_client(barber.user).delete(f"/api/v1/barber/services/{service.id}/")

        assert response.status_code == 204
        service.refresh_from_db()
        assert service.is_active is False

    def test_foreign_service_404(self, api_client, make_auth_client):
        foreign = ServiceFactory()  # boshqa sartaroshniki
        other = BarberProfileFactory()

        response = make_auth_client(other.user).patch(
            f"/api/v1/barber/services/{foreign.id}/", {"price": "1.00"}, format="json"
        )

        assert response.status_code == 404


class TestWeekSchedule:
    def test_get_empty(self, api_client, make_auth_client):
        barber = BarberProfileFactory()

        response = make_auth_client(barber.user).get("/api/v1/barber/schedule/")

        assert response.status_code == 200
        assert response.json()["schedule"] == []

    def test_put(self, api_client, make_auth_client):
        barber = BarberProfileFactory()
        rows = [
            {"weekday": Weekday.MONDAY, "start_time": "09:00:00", "end_time": "18:00:00"},
            {"weekday": Weekday.TUESDAY, "start_time": "09:00:00", "end_time": "15:00:00"},
        ]

        response = make_auth_client(barber.user).put(
            "/api/v1/barber/schedule/", {"schedule": rows}, format="json"
        )

        assert response.status_code == 200
        assert len(response.json()["schedule"]) == 2

    def test_put_duplicate_weekday_rejected(self, api_client, make_auth_client):
        barber = BarberProfileFactory()
        rows = [
            {"weekday": Weekday.MONDAY, "start_time": "09:00:00", "end_time": "18:00:00"},
            {"weekday": Weekday.MONDAY, "start_time": "10:00:00", "end_time": "15:00:00"},
        ]

        response = make_auth_client(barber.user).put(
            "/api/v1/barber/schedule/", {"schedule": rows}, format="json"
        )

        assert response.status_code == 400

    def test_put_bad_time_order_rejected(self, api_client, make_auth_client):
        barber = BarberProfileFactory()
        rows = [
            {"weekday": Weekday.MONDAY, "start_time": "18:00:00", "end_time": "09:00:00"},
        ]

        response = make_auth_client(barber.user).put(
            "/api/v1/barber/schedule/", {"schedule": rows}, format="json"
        )

        assert response.status_code == 400


class TestBreaks:
    def test_create_within_work_hours(self, api_client, make_auth_client):
        barber = BarberProfileFactory()
        WorkScheduleFactory(barber=barber, weekday=Weekday.MONDAY)

        response = make_auth_client(barber.user).post(
            "/api/v1/barber/schedule/breaks/",
            {"weekday": Weekday.MONDAY, "start_time": "13:00:00", "end_time": "14:00:00"},
            format="json",
        )

        assert response.status_code == 201

    def test_create_without_schedule_rejected(self, api_client, make_auth_client):
        barber = BarberProfileFactory()

        response = make_auth_client(barber.user).post(
            "/api/v1/barber/schedule/breaks/",
            {"weekday": Weekday.MONDAY, "start_time": "13:00:00", "end_time": "14:00:00"},
            format="json",
        )

        assert response.status_code == 400

    def test_create_outside_hours_rejected(self, api_client, make_auth_client):
        barber = BarberProfileFactory()
        WorkScheduleFactory(barber=barber, weekday=Weekday.MONDAY)  # 09:00-18:00

        response = make_auth_client(barber.user).post(
            "/api/v1/barber/schedule/breaks/",
            {"weekday": Weekday.MONDAY, "start_time": "12:00:00", "end_time": "19:00:00"},
            format="json",
        )

        assert response.status_code == 400

    def test_list(self, api_client, make_auth_client):
        barber = BarberProfileFactory()
        break_obj = ScheduleBreakFactory(schedule__barber=barber)

        response = make_auth_client(barber.user).get("/api/v1/barber/schedule/breaks/")

        assert response.status_code == 200
        assert [row["id"] for row in response.json()] == [break_obj.id]

    def test_delete(self, api_client, make_auth_client):
        barber = BarberProfileFactory()
        break_obj = ScheduleBreakFactory(schedule__barber=barber)

        response = make_auth_client(barber.user).delete(
            f"/api/v1/barber/schedule/breaks/{break_obj.id}/"
        )

        assert response.status_code == 204

    def test_delete_foreign_rejected(self, api_client, make_auth_client):
        foreign = ScheduleBreakFactory()  # boshqa sartaroshniki
        other = BarberProfileFactory()

        response = make_auth_client(other.user).delete(
            f"/api/v1/barber/schedule/breaks/{foreign.id}/"
        )

        assert response.status_code == 400


class TestDayOffs:
    def test_create_and_list(self, api_client, make_auth_client):
        barber = BarberProfileFactory()
        day = timezone.localdate() + timedelta(days=10)

        response = make_auth_client(barber.user).post(
            "/api/v1/barber/day-offs/", {"date": day.isoformat(), "reason": "Ta'til"}, format="json"
        )

        assert response.status_code == 201

        listing = make_auth_client(barber.user).get("/api/v1/barber/day-offs/")
        assert [row["date"] for row in listing.json()] == [day.isoformat()]

    def test_delete(self, api_client, make_auth_client):
        barber = BarberProfileFactory()
        day_off = DayOffFactory(barber=barber)

        response = make_auth_client(barber.user).delete(f"/api/v1/barber/day-offs/{day_off.id}/")

        assert response.status_code == 204

    def test_delete_foreign_rejected(self, api_client, make_auth_client):
        foreign = DayOffFactory()  # boshqa sartaroshniki
        other = BarberProfileFactory()

        response = make_auth_client(other.user).delete(f"/api/v1/barber/day-offs/{foreign.id}/")

        assert response.status_code == 400


class TestStatusToggle:
    def test_activate(self, api_client, make_auth_client):
        barber = BarberProfileFactory()

        response = make_auth_client(barber.user).post(
            "/api/v1/barber/status/", {"is_active": True}, format="json"
        )

        assert response.status_code == 200
        assert response.json()["is_active_now"] is True
        barber.refresh_from_db()
        assert barber.is_active_now is True

    def test_deactivate(self, api_client, make_auth_client):
        barber = BarberProfileFactory(is_active_now=True)

        response = make_auth_client(barber.user).post(
            "/api/v1/barber/status/", {"is_active": False}, format="json"
        )

        assert response.status_code == 200
        assert response.json()["is_active_now"] is False

    def test_client_role_rejected(self, api_client, make_auth_client):
        response = make_auth_client(UserFactory()).post(
            "/api/v1/barber/status/", {"is_active": True}, format="json"
        )

        assert response.status_code == 403
