"""Bosqich 5: salon egasi va super admin API testlari (moderatsiya, statistika)."""

import pytest

from apps.accounts.factories import UserFactory
from apps.accounts.models import User
from apps.barbers.factories import BarberProfileFactory
from apps.bookings.factories import AppointmentFactory
from apps.salons.factories import SalonFactory
from apps.salons.models import SalonStatus

pytestmark = pytest.mark.django_db


class TestSalonProfile:
    def test_get_own(self, api_client, make_auth_client):
        salon = SalonFactory()

        response = make_auth_client(salon.owner).get("/api/v1/salon/profile/")

        assert response.status_code == 200
        assert response.json()["name"] == salon.name

    def test_get_without_salon_404(self, api_client, make_auth_client):
        owner = UserFactory(role=User.Role.SALON_ADMIN)

        response = make_auth_client(owner).get("/api/v1/salon/profile/")

        assert response.status_code == 404

    def test_patch(self, api_client, make_auth_client):
        salon = SalonFactory()

        response = make_auth_client(salon.owner).patch(
            "/api/v1/salon/profile/", {"name": "Yangi nom", "phone": "+998901112233"}, format="json"
        )

        assert response.status_code == 200
        salon.refresh_from_db()
        assert salon.name == "Yangi nom"

    def test_status_not_editable_by_owner(self, api_client, make_auth_client):
        salon = SalonFactory(status=SalonStatus.PENDING)

        response = make_auth_client(salon.owner).patch(
            "/api/v1/salon/profile/", {"name": "Yangi nom", "status": "approved"}, format="json"
        )

        assert response.status_code == 200
        salon.refresh_from_db()
        assert salon.name == "Yangi nom"
        assert salon.status == SalonStatus.PENDING  # moderatsiya — faqat admin

    def test_barber_role_rejected(self, api_client, make_auth_client):
        barber = BarberProfileFactory()

        response = make_auth_client(barber.user).get("/api/v1/salon/profile/")

        assert response.status_code == 403


class TestSalonBarbers:
    def test_lists_own_salon_barbers(self, api_client, make_auth_client):
        salon = SalonFactory()
        barber = BarberProfileFactory(salon=salon)
        BarberProfileFactory()  # boshqa salonniki

        response = make_auth_client(salon.owner).get("/api/v1/salon/barbers/")

        assert response.status_code == 200
        assert [row["id"] for row in response.json()] == [barber.id]

    def test_empty_salon(self, api_client, make_auth_client):
        salon = SalonFactory()

        response = make_auth_client(salon.owner).get("/api/v1/salon/barbers/")

        assert response.status_code == 200
        assert response.json() == []


class TestAdminSalons:
    def test_list_and_status_filter(self, api_client, make_auth_client):
        admin = UserFactory(role=User.Role.SUPERADMIN)
        approved = SalonFactory()
        pending = SalonFactory(status=SalonStatus.PENDING)
        auth = make_auth_client(admin)

        response = auth.get("/api/v1/admin/salons/")
        assert response.status_code == 200
        assert {row["id"] for row in response.json()} == {approved.id, pending.id}

        response = auth.get("/api/v1/admin/salons/", {"status": "pending"})
        assert [row["id"] for row in response.json()] == [pending.id]

    def test_non_admin_rejected(self, api_client, make_auth_client):
        response = make_auth_client(UserFactory()).get("/api/v1/admin/salons/")

        assert response.status_code == 403

    def test_approve_pending(self, api_client, make_auth_client):
        admin = UserFactory(role=User.Role.SUPERADMIN)
        salon = SalonFactory(status=SalonStatus.PENDING)

        response = make_auth_client(admin).post(f"/api/v1/admin/salons/{salon.id}/approve/")

        assert response.status_code == 200
        assert response.json()["status"] == "approved"
        salon.refresh_from_db()
        assert salon.status == SalonStatus.APPROVED

    def test_approve_already_approved_rejected(self, api_client, make_auth_client):
        admin = UserFactory(role=User.Role.SUPERADMIN)
        salon = SalonFactory(status=SalonStatus.APPROVED)

        response = make_auth_client(admin).post(f"/api/v1/admin/salons/{salon.id}/approve/")

        assert response.status_code == 400

    def test_block(self, api_client, make_auth_client):
        admin = UserFactory(role=User.Role.SUPERADMIN)
        salon = SalonFactory(status=SalonStatus.APPROVED)

        response = make_auth_client(admin).post(f"/api/v1/admin/salons/{salon.id}/block/")

        assert response.status_code == 200
        salon.refresh_from_db()
        assert salon.status == SalonStatus.BLOCKED


class TestAdminStats:
    def test_stats_counts(self, api_client, make_auth_client):
        admin = UserFactory(role=User.Role.SUPERADMIN)
        BarberProfileFactory()
        AppointmentFactory()

        response = make_auth_client(admin).get("/api/v1/admin/stats/")

        assert response.status_code == 200
        data = response.json()
        assert data["users"]["total"] >= 1
        assert data["barbers_total"] >= 1
        assert data["appointments"]["total"] >= 1
        assert "salons" in data

    def test_requires_superadmin(self, api_client, make_auth_client):
        response = make_auth_client(UserFactory()).get("/api/v1/admin/stats/")

        assert response.status_code == 403
