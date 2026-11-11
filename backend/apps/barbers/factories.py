"""Sartarosh va sevimli factory'lari."""

import factory

from apps.accounts.factories import UserFactory
from apps.accounts.models import User
from apps.barbers.models import BarberProfile, BarberStatus, Favorite
from apps.salons.factories import SalonFactory


class BarberProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BarberProfile

    user = factory.SubFactory(UserFactory, role=User.Role.BARBER)
    salon = factory.SubFactory(SalonFactory)
    bio = factory.Sequence(lambda n: f"Sartarosh bio {n + 1}")
    experience_years = factory.Sequence(lambda n: (n % 15) + 1)
    status = BarberStatus.APPROVED


class FavoriteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Favorite

    client = factory.SubFactory(UserFactory)
    barber = factory.SubFactory(BarberProfileFactory)
