"""Bosqich 5: katalog API testlari (viloyatlar, salonlar, sartaroshlar, slotlar).

Barcha endpointlar ochiq (AllowAny) — faqat APPROVED holatdagi
salon/sartaroshlar ko'rinadi (moderatsiya qoidasi).
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.barbers.factories import BarberProfileFactory
from apps.barbers.models import BarberStatus
from apps.core.factories import DistrictFactory, RegionFactory
from apps.salons.factories import SalonFactory
from apps.salons.models import SalonStatus
from apps.schedule.factories import WorkScheduleFactory
from apps.services.factories import ServiceFactory
from apps.services.models import ServiceOwner

pytestmark = pytest.mark.django_db


class TestRegions:
    def test_regions_list(self, api_client):
        region = RegionFactory()

        response = api_client.get("/api/v1/catalog/regions/")

        assert response.status_code == 200
        assert [row["name"] for row in response.json()] == [region.name]

    def test_districts_action(self, api_client):
        district = DistrictFactory()

        response = api_client.get(f"/api/v1/catalog/regions/{district.region_id}/districts/")

        assert response.status_code == 200
        assert [row["id"] for row in response.json()] == [district.id]


class TestSalons:
    def test_list_shows_only_approved(self, api_client):
        approved = SalonFactory()
        SalonFactory(status=SalonStatus.PENDING)

        response = api_client.get("/api/v1/catalog/salons/")

        assert response.status_code == 200
        ids = [row["id"] for row in response.json()["results"]]
        assert ids == [approved.id]

    def test_region_filter(self, api_client):
        salon = SalonFactory()
        SalonFactory()  # boshqa hududda

        response = api_client.get("/api/v1/catalog/salons/", {"region": salon.region_id})

        ids = [row["id"] for row in response.json()["results"]]
        assert salon.id in ids and len(ids) == 1

    def test_district_filter(self, api_client):
        salon = SalonFactory()
        SalonFactory()  # boshqa tuman

        response = api_client.get("/api/v1/catalog/salons/", {"district": salon.district_id})

        ids = [row["id"] for row in response.json()["results"]]
        assert salon.id in ids and len(ids) == 1

    def test_search_filter(self, api_client):
        salon = SalonFactory()
        SalonFactory()  # boshqa nom

        response = api_client.get("/api/v1/catalog/salons/", {"search": salon.name})

        ids = [row["id"] for row in response.json()["results"]]
        assert salon.id in ids and len(ids) == 1

    def test_retrieve(self, api_client):
        salon = SalonFactory()

        response = api_client.get(f"/api/v1/catalog/salons/{salon.id}/")

        assert response.status_code == 200
        assert response.json()["name"] == salon.name

    def test_pending_salon_hidden(self, api_client):
        salon = SalonFactory(status=SalonStatus.PENDING)

        assert api_client.get(f"/api/v1/catalog/salons/{salon.id}/").status_code == 404


class TestBarbers:
    def test_list_shows_only_approved(self, api_client):
        approved = BarberProfileFactory()
        BarberProfileFactory(status=BarberStatus.PENDING)

        response = api_client.get("/api/v1/catalog/barbers/")

        assert response.status_code == 200
        ids = [row["id"] for row in response.json()["results"]]
        assert ids == [approved.id]

    def test_filters(self, api_client):
        barber = BarberProfileFactory(is_active_now=True)
        BarberProfileFactory()  # boshqa salon, nofaol

        response = api_client.get("/api/v1/catalog/barbers/", {"salon": barber.salon_id})
        assert [row["id"] for row in response.json()["results"]] == [barber.id]

        response = api_client.get("/api/v1/catalog/barbers/", {"is_active": "true"})
        assert [row["id"] for row in response.json()["results"]] == [barber.id]

        response = api_client.get("/api/v1/catalog/barbers/", {"search": barber.user.full_name})
        assert [row["id"] for row in response.json()["results"]] == [barber.id]

    def test_retrieve(self, api_client):
        barber = BarberProfileFactory()

        response = api_client.get(f"/api/v1/catalog/barbers/{barber.id}/")

        assert response.status_code == 200
        assert response.json()["name"] == barber.user.full_name

    def test_services_action_includes_barber_and_salon_services(self, api_client):
        barber = BarberProfileFactory()
        own = ServiceFactory(barber=barber)
        salon_service = ServiceFactory(
            owner_type=ServiceOwner.SALON, barber=None, salon=barber.salon
        )
        ServiceFactory()  # boshqa sartaroshniki

        response = api_client.get(f"/api/v1/catalog/barbers/{barber.id}/services/")

        assert response.status_code == 200
        names = {row["name"] for row in response.json()}
        assert names == {own.name, salon_service.name}

    def test_slots_happy(self, api_client):
        barber = BarberProfileFactory()
        day = timezone.localdate() + timedelta(days=1)
        WorkScheduleFactory(barber=barber, weekday=day.weekday())  # 09:00-18:00
        service = ServiceFactory(barber=barber, duration_min=30)

        response = api_client.get(
            f"/api/v1/catalog/barbers/{barber.id}/slots/",
            {"service_id": service.id, "day": day.isoformat()},
        )

        assert response.status_code == 200
        slots = response.json()
        assert len(slots) == 35  # 09:00–18:00, 15 daq qadam, tanaffussiz
        assert slots[0]["start"] == "09:00:00"

    def test_slots_without_schedule_empty(self, api_client):
        barber = BarberProfileFactory()
        day = timezone.localdate() + timedelta(days=1)
        service = ServiceFactory(barber=barber)

        response = api_client.get(
            f"/api/v1/catalog/barbers/{barber.id}/slots/",
            {"service_id": service.id, "day": day.isoformat()},
        )

        assert response.status_code == 200
        assert response.json() == []

    def test_slots_other_barbers_service_rejected(self, api_client):
        barber = BarberProfileFactory()
        day = timezone.localdate() + timedelta(days=1)
        WorkScheduleFactory(barber=barber, weekday=day.weekday())
        other_service = ServiceFactory()  # boshqa sartaroshniki

        response = api_client.get(
            f"/api/v1/catalog/barbers/{barber.id}/slots/",
            {"service_id": other_service.id, "day": day.isoformat()},
        )

        assert response.status_code == 400

    def test_slots_invalid_params_rejected(self, api_client):
        barber = BarberProfileFactory()
        day = timezone.localdate() + timedelta(days=1)

        # service_id yo'q
        response = api_client.get(
            f"/api/v1/catalog/barbers/{barber.id}/slots/", {"day": day.isoformat()}
        )
        assert response.status_code == 400

        # sana formati noto'g'ri
        response = api_client.get(
            f"/api/v1/catalog/barbers/{barber.id}/slots/",
            {"service_id": 1, "day": "not-a-date"},
        )
        assert response.status_code == 400
