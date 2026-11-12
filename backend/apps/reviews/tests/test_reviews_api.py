"""Bosqich 5: sharh API testlari (COMPLETED sharti, 1:1, rating qayta hisoblash)."""

from datetime import time

import pytest

from apps.accounts.factories import UserFactory
from apps.barbers.factories import BarberProfileFactory
from apps.bookings.factories import AppointmentFactory
from apps.bookings.models import AppointmentStatus
from apps.reviews.factories import ReviewFactory

pytestmark = pytest.mark.django_db


class TestCreateReview:
    def test_happy_and_rating_recompute(self, api_client, make_auth_client):
        appt = AppointmentFactory(status=AppointmentStatus.COMPLETED)

        response = make_auth_client(appt.client).post(
            "/api/v1/reviews/",
            {"appointment": appt.id, "rating": 5, "comment": "Zo'r ish"},
            format="json",
        )

        assert response.status_code == 201
        assert response.json()["rating"] == 5
        appt.barber.refresh_from_db()
        assert appt.barber.rating_count == 1
        assert float(appt.barber.rating_avg) == 5.0

    def test_duplicate_rejected(self, api_client, make_auth_client):
        appt = AppointmentFactory(status=AppointmentStatus.COMPLETED)
        ReviewFactory(appointment=appt)
        auth = make_auth_client(appt.client)

        response = auth.post(
            "/api/v1/reviews/", {"appointment": appt.id, "rating": 4}, format="json"
        )

        assert response.status_code == 400

    def test_not_completed_rejected(self, api_client, make_auth_client):
        appt = AppointmentFactory()  # PENDING

        response = make_auth_client(appt.client).post(
            "/api/v1/reviews/", {"appointment": appt.id, "rating": 5}, format="json"
        )

        assert response.status_code == 400

    def test_foreign_appointment_403(self, api_client, make_auth_client):
        appt = AppointmentFactory(status=AppointmentStatus.COMPLETED)

        response = make_auth_client(UserFactory()).post(
            "/api/v1/reviews/", {"appointment": appt.id, "rating": 5}, format="json"
        )

        assert response.status_code == 403

    def test_invalid_rating_rejected(self, api_client, make_auth_client):
        appt = AppointmentFactory(status=AppointmentStatus.COMPLETED)

        response = make_auth_client(appt.client).post(
            "/api/v1/reviews/", {"appointment": appt.id, "rating": 6}, format="json"
        )

        assert response.status_code == 400


class TestPublicBarberReviews:
    def test_lists_visible_only(self, api_client):
        barber = BarberProfileFactory()
        appt1 = AppointmentFactory(barber=barber, status=AppointmentStatus.COMPLETED)
        visible = ReviewFactory(appointment=appt1, rating=4)
        appt2 = AppointmentFactory(
            barber=barber,
            status=AppointmentStatus.COMPLETED,
            start_time=time(11, 0),
            end_time=time(11, 30),
        )
        ReviewFactory(appointment=appt2, rating=5, is_visible=False)

        response = api_client.get(f"/api/v1/reviews/barber/{barber.id}/")

        assert response.status_code == 200
        data = response.json()
        assert [row["id"] for row in data] == [visible.id]
        assert data[0]["rating"] == 4

    def test_unknown_barber_404(self, api_client):
        response = api_client.get("/api/v1/reviews/barber/999999/")

        assert response.status_code == 404
