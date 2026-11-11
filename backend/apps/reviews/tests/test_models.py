"""Bosqich 2: Review model testlari."""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.bookings.factories import AppointmentFactory
from apps.bookings.models import AppointmentStatus
from apps.reviews.factories import ReviewFactory
from apps.reviews.models import Review

pytestmark = pytest.mark.django_db


class TestReview:
    def test_defaults(self):
        review = ReviewFactory()

        assert review.rating == 5
        assert review.is_visible is True
        assert review.barber_reply == ""

    def test_str(self):
        review = ReviewFactory(rating=4)

        assert str(review).endswith("4/5")

    def test_one_review_per_appointment(self):
        review = ReviewFactory()

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Review.objects.create(
                    appointment=review.appointment,
                    client=review.client,
                    barber=review.barber,
                    rating=4,
                )

    def test_rating_validator_bounds(self):
        review = ReviewFactory()

        for bad in (0, 6):
            review.rating = bad
            with pytest.raises(ValidationError):
                review.full_clean()

    def test_rating_valid_values(self):
        review = ReviewFactory(rating=1)

        review.full_clean()  # xato bo'lmasligi kerak
        assert review.rating == 1

    def test_matches_completed_appointment_parties(self):
        appt = AppointmentFactory(status=AppointmentStatus.COMPLETED)
        review = ReviewFactory(appointment=appt)

        assert review.client == appt.client
        assert review.barber == appt.barber
