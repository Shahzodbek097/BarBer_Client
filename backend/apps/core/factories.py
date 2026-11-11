"""Factory'lar: hududlar (boshqa app factory'lari ishlatadi)."""

import factory

from apps.core.models import District, Region


class RegionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Region
        django_get_or_create = ("name",)

    name = factory.Sequence(lambda n: f"Viloyat {n + 1}")


class DistrictFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = District
        django_get_or_create = ("region", "name")

    region = factory.SubFactory(RegionFactory)
    name = factory.Sequence(lambda n: f"Tuman {n + 1}")
