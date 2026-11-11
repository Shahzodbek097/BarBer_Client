"""Bosqich 2: Salon model testlari."""

import pytest
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError

from apps.accounts.factories import UserFactory
from apps.accounts.models import User
from apps.core.factories import RegionFactory
from apps.salons.factories import SalonFactory
from apps.salons.models import Salon, SalonStatus

pytestmark = pytest.mark.django_db


class TestSalon:
    def test_factory_defaults(self):
        salon = SalonFactory()

        assert salon.status == SalonStatus.APPROVED  # factory default
        assert salon.rating_avg == 0
        assert salon.rating_count == 0
        assert salon.is_deleted is False
        assert salon.photos == []
        assert salon.owner.role == User.Role.SALON_ADMIN

    def test_model_default_status_is_pending(self):
        salon = Salon.objects.create(
            owner=UserFactory(role=User.Role.SALON_ADMIN),
            name="Yangi salon",
            slug="yangi-salon",
            region=RegionFactory(),
        )

        assert salon.status == SalonStatus.PENDING

    def test_str(self):
        assert str(SalonFactory(name="Chevar")) == "Chevar"

    def test_slug_unique(self):
        SalonFactory(slug="salon-test")

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Salon.objects.create(
                    owner=UserFactory(role=User.Role.SALON_ADMIN),
                    name="Nusxa",
                    slug="salon-test",
                    region=RegionFactory(),
                )

    def test_region_delete_protected(self):
        salon = SalonFactory()

        with pytest.raises(ProtectedError):
            salon.region.delete()

    def test_owner_delete_protected(self):
        salon = SalonFactory()

        with pytest.raises(ProtectedError):
            salon.owner.delete()
