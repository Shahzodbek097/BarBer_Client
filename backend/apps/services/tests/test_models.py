"""Bosqich 2: ServiceCategory, Service model testlari (xor constraint bilan)."""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.salons.factories import SalonFactory
from apps.services.factories import ServiceCategoryFactory, ServiceFactory
from apps.services.models import Service, ServiceCategory, ServiceOwner

pytestmark = pytest.mark.django_db


class TestServiceCategory:
    def test_str(self):
        assert str(ServiceCategoryFactory(name="Soch")) == "Soch"

    def test_slug_unique(self):
        ServiceCategoryFactory(slug="soch")

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ServiceCategory.objects.create(name="Boshqa soch", slug="soch")


class TestServiceOwnerXor:
    def test_barber_owned_service_valid(self):
        service = ServiceFactory(owner_type=ServiceOwner.BARBER)

        assert service.barber is not None
        assert service.salon is None

    def test_salon_owned_service_valid(self):
        service = ServiceFactory(owner_type=ServiceOwner.SALON, barber=None, salon=SalonFactory())

        assert service.salon is not None
        assert service.barber is None

    def test_both_owners_rejected(self):
        service = ServiceFactory()  # sartaroshga tegishli
        service.salon = SalonFactory()

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                service.save()

    def test_no_owner_rejected(self):
        service = ServiceFactory()
        service.barber = None

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                service.save()


class TestServiceConstraints:
    def test_duration_must_be_positive(self):
        service = ServiceFactory()

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Service.objects.filter(pk=service.pk).update(duration_min=0)

    def test_price_non_negative(self):
        service = ServiceFactory()

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Service.objects.filter(pk=service.pk).update(price=Decimal("-1"))

    def test_duration_validator(self):
        service = ServiceFactory()
        service.duration_min = 0

        with pytest.raises(ValidationError):
            service.full_clean()

    def test_price_validator(self):
        service = ServiceFactory()
        service.price = Decimal("-1")

        with pytest.raises(ValidationError):
            service.full_clean()

    def test_str_shows_duration(self):
        service = ServiceFactory(name="Soch kesish", duration_min=30)

        assert str(service) == "Soch kesish (30 min)"
