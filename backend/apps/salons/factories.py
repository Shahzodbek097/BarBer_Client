"""Salon factory."""

import factory

from apps.accounts.factories import UserFactory
from apps.accounts.models import User
from apps.core.factories import DistrictFactory
from apps.salons.models import Salon, SalonStatus


class SalonFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Salon
        django_get_or_create = ("slug",)

    owner = factory.SubFactory(UserFactory, role=User.Role.SALON_ADMIN)
    district = factory.SubFactory(DistrictFactory)
    # region har doim district.region bilan bir xil bo'lishi shart
    region = factory.SelfAttribute("district.region")
    name = factory.Sequence(lambda n: f"Sartaroshxona {n + 1}")
    slug = factory.Sequence(lambda n: f"salon-{n + 1}")
    address = factory.Sequence(lambda n: f"Ko'cha {n + 1}, {n + 1}-uy")
    # Factory default: katalog testlari uchun APPROVED; model default PENDING
    status = SalonStatus.APPROVED
