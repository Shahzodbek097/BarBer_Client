"""Sartarosh kabineti API serializatorlari (bosqich 5)."""

from rest_framework import serializers

from apps.barbers.models import BarberProfile
from apps.schedule.models import DayOff, ScheduleBreak, WorkSchedule
from apps.services.models import Service, ServiceCategory


class BarberProfileSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="user.full_name", read_only=True)
    specialties = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = BarberProfile
        fields = (
            "id",
            "name",
            "bio",
            "experience_years",
            "specialties",
            "portfolio_images",
            "salon",
            "rating_avg",
            "rating_count",
            "is_active_now",
            "status",
        )
        read_only_fields = (
            "id",
            "name",
            "salon",
            "rating_avg",
            "rating_count",
            "is_active_now",
            "status",
        )


class ProfileCreateSerializer(serializers.Serializer):
    """POST /barber/profile/ — onboarding."""

    bio = serializers.CharField(max_length=2000, required=False, allow_blank=True, default="")
    experience_years = serializers.IntegerField(
        required=False, default=0, min_value=0, max_value=60
    )


class ProfileUpdateSerializer(serializers.Serializer):
    """PATCH /barber/profile/ — bio, tajriba, portfolio, mutaxassisliklar."""

    bio = serializers.CharField(max_length=2000, required=False, allow_blank=True)
    experience_years = serializers.IntegerField(required=False, min_value=0, max_value=60)
    portfolio_images = serializers.ListField(
        child=serializers.CharField(max_length=300), required=False
    )
    specialties = serializers.ListField(
        child=serializers.IntegerField(), required=False, allow_empty=True
    )


class ServiceCategoryField(serializers.PrimaryKeyRelatedField):
    queryset = ServiceCategory.objects.all()


class BarberServiceSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Service
        fields = (
            "id",
            "category",
            "category_name",
            "name",
            "duration_min",
            "price",
            "description",
            "is_active",
        )
        read_only_fields = ("id", "category_name", "is_active")


class BarberServiceWriteSerializer(serializers.ModelSerializer):
    """POST/PATCH /barber/services/ — sartarosh o'z xizmatini yozadi."""

    category = ServiceCategoryField()

    class Meta:
        model = Service
        fields = ("category", "name", "duration_min", "price", "description")


class WorkScheduleSerializer(serializers.ModelSerializer):
    weekday = serializers.ChoiceField(choices=WorkSchedule._meta.get_field("weekday").choices)

    class Meta:
        model = WorkSchedule
        fields = ("weekday", "start_time", "end_time", "is_working")

    def validate(self, attrs):
        if attrs["start_time"] >= attrs["end_time"]:
            raise serializers.ValidationError("Ish boshlanishi tugashidan oldin bo'lishi kerak.")
        return attrs


class WeekSchedulePutSerializer(serializers.Serializer):
    """PUT /barber/schedule/ — haftalik jadval (7 yozuv yoki kamroq)."""

    schedule = WorkScheduleSerializer(many=True)


class ScheduleBreakSerializer(serializers.ModelSerializer):
    schedule = serializers.PrimaryKeyRelatedField(read_only=True)
    # UI'da kun nomini ko'rsatish uchun (jadval bilan bog'liq)
    weekday = serializers.IntegerField(source="schedule.weekday", read_only=True)

    class Meta:
        model = ScheduleBreak
        fields = ("id", "schedule", "weekday", "start_time", "end_time")
        read_only_fields = ("id", "schedule", "weekday")


class BreakCreateSerializer(serializers.Serializer):
    weekday = serializers.ChoiceField(choices=WorkSchedule._meta.get_field("weekday").choices)
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()


class DayOffSerializer(serializers.ModelSerializer):
    class Meta:
        model = DayOff
        fields = ("id", "date", "reason")


class DayOffCreateSerializer(serializers.Serializer):
    date = serializers.DateField()
    reason = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")


class StatusToggleSerializer(serializers.Serializer):
    is_active = serializers.BooleanField()
