"""Xizmat factory'lari."""

from decimal import Decimal

import factory

from apps.barbers.factories import BarberProfileFactory
from apps.services.models import Service, ServiceCategory, ServiceOwner


class ServiceCategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ServiceCategory
        django_get_or_create = ("slug",)

    name = factory.Sequence(lambda n: f"Kategoriya {n + 1}")
    slug = factory.Sequence(lambda n: f"kategoriya-{n + 1}")


class ServiceFactory(factory.django.DjangoModelFactory):
    """Default: sartaroshga tegishli xizmat (owner_type=barber, salon=None)."""

    class Meta:
        model = Service

    barber = factory.SubFactory(BarberProfileFactory)
    category = factory.SubFactory(ServiceCategoryFactory)
    name = factory.Sequence(lambda n: f"Xizmat {n + 1}")
    owner_type = ServiceOwner.BARBER
    duration_min = 30
    price = Decimal("50000.00")
