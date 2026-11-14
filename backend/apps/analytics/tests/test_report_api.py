"""Hisobot API testlari (rol izolyatsiyasi + Excel eksport)."""

from datetime import timedelta
from io import BytesIO

import pytest
from django.utils import timezone
from openpyxl import load_workbook
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.models import User
from apps.analytics.services.xlsx import XLSX_CONTENT_TYPE
from apps.barbers.factories import BarberProfileFactory
from apps.bookings.factories import AppointmentFactory
from apps.bookings.models import AppointmentStatus
from apps.salons.factories import SalonFactory
from apps.salons.models import SalonStatus

pytestmark = pytest.mark.django_db


def _completed(barber, **kwargs):
    # hisobotlar default bugun bo'lgani uchun navbat ham bugun yaratiladi
    kwargs.setdefault("date", timezone.localdate())
    return AppointmentFactory(barber=barber, status=AppointmentStatus.COMPLETED, **kwargs)


class TestBarberReportApi:
    def test_json_report(self, api_client, make_auth_client):
        barber = BarberProfileFactory()
        _completed(barber)

        response = make_auth_client(barber.user).get("/api/v1/barber/report/")

        assert response.status_code == 200
        data = response.json()
        assert data["totals"]["all"] == 1
        assert float(data["totals"]["revenue"]) == 50000.0
        assert data["rows"][0]["service"]

    def test_only_own_data(self, api_client, make_auth_client):
        mine = BarberProfileFactory()
        other = BarberProfileFactory()
        _completed(mine)
        _completed(other)

        data = make_auth_client(mine.user).get("/api/v1/barber/report/").json()

        assert data["totals"]["all"] == 1
        assert data["barber"]["id"] == mine.pk

    def test_client_role_403(self, api_client, make_auth_client):
        user = UserFactory(role=User.Role.CLIENT)
        assert make_auth_client(user).get("/api/v1/barber/report/").status_code == 403

    def test_unauthenticated_401(self, api_client):
        assert api_client.get("/api/v1/barber/report/").status_code == 401

    def test_xlsx_export(self, api_client, make_auth_client):
        barber = BarberProfileFactory()
        _completed(barber)

        response = make_auth_client(barber.user).get("/api/v1/barber/report/", {"format": "xlsx"})

        assert response.status_code == 200
        assert response["Content-Type"] == XLSX_CONTENT_TYPE
        assert "barber-report-" in response["Content-Disposition"]
        wb = load_workbook(BytesIO(response.content))
        ws = wb.active
        assert ws.cell(1, 2).value == "Mijoz"
        assert ws.cell(2, 2).value  # mijoz nomi yozilgan


class TestSalonReportApi:
    def test_json_report(self, api_client, make_auth_client):
        salon = SalonFactory()
        barber = BarberProfileFactory(salon=salon)
        _completed(barber)

        data = make_auth_client(salon.owner).get("/api/v1/salon/report/").json()

        assert data["totals"]["total"] == 1
        assert float(data["totals"]["revenue"]) == 50000.0
        assert data["rows"][0]["barber_id"] == barber.pk

    def test_isolation_between_salons(self, api_client, make_auth_client):
        salon_a = SalonFactory()
        salon_b = SalonFactory()
        _completed(BarberProfileFactory(salon=salon_a))
        _completed(BarberProfileFactory(salon=salon_b))

        data = make_auth_client(salon_a.owner).get("/api/v1/salon/report/").json()

        assert data["totals"]["total"] == 1

    def test_owner_without_salon_404(self, api_client, make_auth_client):
        owner = UserFactory(role=User.Role.SALON_ADMIN)
        assert make_auth_client(owner).get("/api/v1/salon/report/").status_code == 404

    def test_barber_role_403(self, api_client, make_auth_client):
        barber = BarberProfileFactory()
        assert make_auth_client(barber.user).get("/api/v1/salon/report/").status_code == 403

    def test_from_to_params(self, api_client, make_auth_client):
        salon = SalonFactory()
        barber = BarberProfileFactory(salon=salon)
        today = timezone.localdate()
        _completed(barber, date=today - timedelta(days=5))
        _completed(barber, date=today)

        data = (
            make_auth_client(salon.owner)
            .get(
                "/api/v1/salon/report/",
                {"from": today.isoformat(), "to": today.isoformat()},
            )
            .json()
        )

        assert data["totals"]["total"] == 1

    def test_xlsx_export_with_totals(self, api_client, make_auth_client):
        salon = SalonFactory()
        barber = BarberProfileFactory(salon=salon)
        _completed(barber)

        response = make_auth_client(salon.owner).get("/api/v1/salon/report/", {"format": "xlsx"})

        assert response.status_code == 200
        wb = load_workbook(BytesIO(response.content))
        ws = wb.active
        assert ws.cell(1, 1).value == "Sartarosh"
        assert ws.cell(4, 1).value == "Jami"  # 3-qator — bo'sh ajratgich
        assert ws.cell(4, 2).value == 1


class TestAdminReportApi:
    def test_superadmin_json(self, api_client, make_auth_client):
        salon = SalonFactory(status=SalonStatus.APPROVED)
        _completed(BarberProfileFactory(salon=salon))
        admin = UserFactory(role=User.Role.SUPERADMIN)

        data = make_auth_client(admin).get("/api/v1/admin/report/").json()

        assert data["totals"]["total"] == 1
        assert data["rows"][0]["salon_id"] == salon.pk

    def test_pending_salon_not_in_report(self, api_client, make_auth_client):
        SalonFactory(status=SalonStatus.PENDING)
        admin = UserFactory(role=User.Role.SUPERADMIN)
        data = make_auth_client(admin).get("/api/v1/admin/report/").json()
        assert data["rows"] == []

    def test_client_role_403(self, api_client, make_auth_client):
        user = UserFactory(role=User.Role.CLIENT)
        assert make_auth_client(user).get("/api/v1/admin/report/").status_code == 403

    def test_xlsx_export(self, api_client, make_auth_client):
        salon = SalonFactory()
        _completed(BarberProfileFactory(salon=salon))
        admin = UserFactory(role=User.Role.SUPERADMIN)

        response = make_auth_client(admin).get("/api/v1/admin/report/", {"format": "xlsx"})

        assert response.status_code == status.HTTP_200_OK
        wb = load_workbook(BytesIO(response.content))
        assert wb.active.cell(1, 1).value == "Salon"
