"""Salon egasi API serializatorlari (bosqich 5)."""

from rest_framework import serializers

from apps.salons.models import Salon


class SalonProfileSerializer(serializers.ModelSerializer):
    region_name = serializers.CharField(source="region.name", read_only=True)
    district_name = serializers.CharField(source="district.name", read_only=True, default=None)

    class Meta:
        model = Salon
        fields = (
            "id",
            "name",
            "slug",
            "region",
            "region_name",
            "district",
            "district_name",
            "address",
            "phone",
            "description",
            "photos",
            "work_time_start",
            "work_time_end",
            "status",
            "rating_avg",
            "rating_count",
        )
        read_only_fields = (
            "id",
            "slug",
            "region",
            "region_name",
            "district",
            "district_name",
            "status",
            "rating_avg",
            "rating_count",
        )


class SalonUpdateSerializer(serializers.ModelSerializer):
    """Salon egasi tahrir qiladigan maydonlar (status/joylashuv emas)."""

    class Meta:
        model = Salon
        fields = (
            "name",
            "address",
            "phone",
            "description",
            "photos",
            "work_time_start",
            "work_time_end",
        )


class SalonBarberSerializer(serializers.Serializer):
    """O'z salonidagi sartaroshlar ro'yxati (salon egasi ko'rinishi)."""

    id = serializers.IntegerField()
    name = serializers.CharField(source="user.full_name")
    experience_years = serializers.IntegerField()
    specialties = serializers.StringRelatedField(many=True)
    rating_avg = serializers.DecimalField(max_digits=3, decimal_places=2)
    rating_count = serializers.IntegerField()
    is_active_now = serializers.BooleanField()
