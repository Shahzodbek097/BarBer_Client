"""Baho factory."""

import factory

from apps.bookings.factories import AppointmentFactory
from apps.reviews.models import Review


class ReviewFactory(factory.django.DjangoModelFactory):
    """Sharh — navbat mijoziga va sartaroshiga avtomatik mos bo'ladi."""

    class Meta:
        model = Review

    appointment = factory.SubFactory(AppointmentFactory)
    client = factory.SelfAttribute("appointment.client")
    barber = factory.SelfAttribute("appointment.barber")
    rating = 5
    comment = factory.Sequence(lambda n: f"Izo {n + 1}")
