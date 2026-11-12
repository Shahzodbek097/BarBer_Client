"""Booking API serializatorlari (bosqich 5).

Kiritish serializatorlari faqat validatsiya qiladi — biznes mantiq
services qatlamida (`create_appointment` va boshqalar).
"""

from rest_framework import serializers

from apps.accounts.models import User
from apps.barbers.models import BarberProfile
from apps.bookings.models import Appointment, AppointmentSource, AppointmentStatus
from apps.services.models import Service


class AppointmentSerializer(serializers.ModelSerializer):
    """Navbat javob serializatori (mijoz va sartarosh kabinetlari)."""

    client_name = serializers.CharField(source="client.full_name", read_only=True)
    client_phone = serializers.CharField(source="client.phone", read_only=True)
    barber_id = serializers.IntegerField(read_only=True)
    service_name = serializers.CharField(source="service.name", read_only=True)
    salon_name = serializers.CharField(source="salon.name", read_only=True, default=None)

    class Meta:
        model = Appointment
        fields = (
            "id",
            "client",
            "client_name",
            "client_phone",
            "barber_id",
            "service",
            "service_name",
            "salon_name",
            "date",
            "start_time",
            "end_time",
            "status",
            "source",
            "price",
            "client_note",
            "barber_reply",
            "created_at",
        )
        read_only_fields = fields


class BookingCreateSerializer(serializers.Serializer):
    """POST /bookings/ kiritish: sartarosh + xizmat + sana + vaqt."""

    barber = serializers.PrimaryKeyRelatedField(queryset=BarberProfile.objects.all())
    service = serializers.PrimaryKeyRelatedField(queryset=Service.objects.all())
    date = serializers.DateField()
    start_time = serializers.TimeField()
    note = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class ManualBookingSerializer(serializers.Serializer):
    """POST /bookings/manual/ — sartarosh orxonadagi mijozga navbat yozadi."""

    client_phone = serializers.CharField(max_length=20)
    service = serializers.PrimaryKeyRelatedField(queryset=Service.objects.all())
    date = serializers.DateField()
    start_time = serializers.TimeField()
    note = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")

    def validate_client_phone(self, value: str) -> str:
        phone = value.strip()
        user = User.objects.filter(phone=phone).first()
        if user is None:
            raise serializers.ValidationError("Bu raqamli mijoz topilmadi.")
        if user.is_blocked:
            raise serializers.ValidationError("Mijoz bloklangan.")
        return phone


class BookingFilterSerializer(serializers.Serializer):
    """Ro'yxat filtrlari: ?status=&day= (query params validatsiyasi)."""

    status = serializers.ChoiceField(
        choices=AppointmentStatus.choices, required=False, allow_blank=True
    )
    day = serializers.DateField(required=False, allow_null=True)


class RescheduleSerializer(serializers.Serializer):
    date = serializers.DateField()
    start_time = serializers.TimeField()


class ProposeSerializer(serializers.Serializer):
    date = serializers.DateField()
    start_time = serializers.TimeField()


class RejectSerializer(serializers.Serializer):
    reply = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


def _valid_source(value: str) -> str:
    valid = {AppointmentSource.ONLINE, AppointmentSource.MANUAL, AppointmentSource.WALK_IN}
    if value not in valid:
        raise serializers.ValidationError("Noma'lum manba.")
    return value


def _valid_status(value: str) -> str:
    if value not in AppointmentStatus.values:
        raise serializers.ValidationError("Noma'lum holat.")
    return value
