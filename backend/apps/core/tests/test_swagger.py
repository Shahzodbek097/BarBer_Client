"""Bosqich 5 gate: Swagger sxemasi barcha majburiy endpointlarni qamrab oladi."""

import pytest

pytestmark = pytest.mark.django_db

REQUIRED_PATHS = (
    # auth (bosqich 3)
    "/api/v1/auth/register/",
    "/api/v1/auth/login/",
    "/api/v1/auth/me/",
    # katalog
    "/api/v1/catalog/regions/",
    "/api/v1/catalog/salons/",
    "/api/v1/catalog/barbers/",
    # navbatlar
    "/api/v1/bookings/",
    "/api/v1/bookings/my/",
    "/api/v1/bookings/incoming/",
    "/api/v1/bookings/manual/",
    "/api/v1/bookings/{id}/cancel/",
    "/api/v1/bookings/{id}/reschedule/",
    "/api/v1/bookings/{id}/confirm/",
    "/api/v1/bookings/{id}/no-show/",
    # sartarosh kabineti
    "/api/v1/barber/profile/",
    "/api/v1/barber/services/",
    "/api/v1/barber/schedule/",
    "/api/v1/barber/schedule/breaks/",
    "/api/v1/barber/day-offs/",
    "/api/v1/barber/status/",
    # salon egasi
    "/api/v1/salon/profile/",
    "/api/v1/salon/barbers/",
    # sharhlar va xabarnomalar
    "/api/v1/reviews/",
    "/api/v1/reviews/barber/{barber_id}/",
    "/api/v1/notifications/",
    # super admin
    "/api/v1/admin/salons/",
    "/api/v1/admin/stats/",
)


class TestSwagger:
    def test_schema_contains_all_required_endpoints(self, api_client):
        response = api_client.get("/api/schema/", HTTP_ACCEPT="application/json")

        assert response.status_code == 200
        paths = response.json()["paths"]
        missing = [path for path in REQUIRED_PATHS if path not in paths]
        assert missing == []

    def test_docs_page_served(self, api_client):
        response = api_client.get("/api/docs/")

        assert response.status_code == 200
