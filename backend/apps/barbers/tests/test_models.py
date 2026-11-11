"""Bosqich 2: BarberProfile va Favorite model testlari."""

import pytest
from django.db import IntegrityError, transaction

from apps.accounts.models import User
from apps.barbers.factories import BarberProfileFactory, FavoriteFactory
from apps.barbers.models import BarberProfile, BarberStatus, Favorite
from apps.services.factories import ServiceCategoryFactory

pytestmark = pytest.mark.django_db


class TestBarberProfile:
    def test_factory_defaults(self):
        barber = BarberProfileFactory()

        assert barber.status == BarberStatus.APPROVED
        assert barber.is_active_now is False
        assert barber.rating_avg == 0
        assert barber.salon is not None  # factory salon bilan yaratadi
        assert barber.user.role == User.Role.BARBER

    def test_salon_is_optional(self):
        barber = BarberProfileFactory(salon=None)

        assert barber.salon is None

    def test_str_uses_user_full_name(self):
        barber = BarberProfileFactory(user__full_name="Kamol")

        assert str(barber) == "Kamol"

    def test_one_profile_per_user(self):
        barber = BarberProfileFactory()

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                BarberProfile.objects.create(user=barber.user)

    def test_specialties_m2m(self):
        barber = BarberProfileFactory()
        category = ServiceCategoryFactory()

        barber.specialties.add(category)

        assert list(barber.specialties.all()) == [category]
        assert list(category.barbers.all()) == [barber]


class TestFavorite:
    def test_str(self):
        fav = FavoriteFactory(client__full_name="Mijoz", barber__user__full_name="Usta")

        assert str(fav) == "Mijoz → Usta"

    def test_unique_client_barber(self):
        fav = FavoriteFactory()

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Favorite.objects.create(client=fav.client, barber=fav.barber)

    def test_related_names_both_directions(self):
        fav = FavoriteFactory()

        assert list(fav.client.favorites.all()) == [fav]
        assert list(fav.barber.favorited_by.all()) == [fav]
