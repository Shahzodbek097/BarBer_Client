"""Bosqich 2: Region, District, AuditLog model testlari."""

import pytest
from django.db import IntegrityError, transaction

from apps.accounts.factories import UserFactory
from apps.core.factories import DistrictFactory, RegionFactory
from apps.core.models import AuditLog, District, Region

pytestmark = pytest.mark.django_db


class TestRegion:
    def test_str(self):
        assert str(RegionFactory(name="Toshkent")) == "Toshkent"

    def test_name_unique(self):
        Region.objects.create(name="Xorazm")

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Region.objects.create(name="Xorazm")

    def test_districts_related(self):
        region = RegionFactory()
        district = DistrictFactory(region=region)

        assert list(region.districts.all()) == [district]


class TestDistrict:
    def test_str_includes_region(self):
        district = DistrictFactory(region__name="Samarqand", name="Urgut")

        assert str(district) == "Samarqand — Urgut"

    def test_name_unique_within_region(self):
        region = RegionFactory()
        District.objects.create(region=region, name="Kattaqo'rg'on")

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                District.objects.create(region=region, name="Kattaqo'rg'on")

    def test_same_name_allowed_in_other_region(self):
        DistrictFactory(region__name="Sirdaryo", name="Guliston")
        other = DistrictFactory(region__name="Surxondaryo", name="Guliston")

        assert other.region.name == "Surxondaryo"


class TestAuditLog:
    def test_defaults(self):
        log = AuditLog.objects.create(
            action="user_registered", model_name="accounts.User", object_id="1"
        )

        assert log.payload == {}
        assert log.actor is None
        assert "user_registered" in str(log)

    def test_actor_can_be_user(self):
        log = AuditLog.objects.create(action="login", actor=UserFactory())

        assert log.actor.phone.startswith("+998")
