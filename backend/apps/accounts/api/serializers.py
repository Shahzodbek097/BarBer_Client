"""Auth API serializatorlari — faqat validatsiya; logika services qatlamida."""

import re

from rest_framework import serializers

from apps.accounts.models import OTPPurpose, User

PHONE_RE = re.compile(r"^\+998\d{9}$")


class PhoneMixin(serializers.Serializer):
    """Telefon maydoni: +998XXXXXXXXX formati (bo'sh joylar olib tashlanadi)."""

    phone = serializers.CharField(max_length=20)

    def validate_phone(self, value: str) -> str:
        phone = value.strip()
        if not PHONE_RE.match(phone):
            raise serializers.ValidationError("Telefon formati: +998XXXXXXXXX")
        return phone


class RegisterSerializer(PhoneMixin):
    """Ro'yxatdan o'tish: mijoz/sartarosh/salon (superadmin — admin paneldan)."""

    full_name = serializers.CharField(max_length=255)
    role = serializers.ChoiceField(
        choices=(
            User.Role.CLIENT,
            User.Role.BARBER,
            User.Role.SALON_ADMIN,
        )
    )

    def validate_phone(self, value: str) -> str:
        phone = super().validate_phone(value)
        if User.objects.filter(phone=phone).exists():
            raise serializers.ValidationError(
                "Bu raqam allaqachon ro'yxatdan o'tgan. Kirish bo'limidan foydalaning."
            )
        return phone

    def validate_full_name(self, value: str) -> str:
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Ism bo'sh bo'lmasligi kerak.")
        return name


class RequestOTPSerializer(PhoneMixin):
    """Kirish: telefon raqamga OTP yuboriladi."""


class VerifyOTPSerializer(PhoneMixin):
    """OTP tekshirish — tokenlarni qaytarish uchun maqsad cheklangan."""

    purpose = serializers.ChoiceField(choices=(OTPPurpose.REGISTRATION, OTPPurpose.LOGIN))
    code = serializers.CharField(min_length=4, max_length=8)


class UserSerializer(serializers.ModelSerializer):
    """Umumiy user ma'lumotlari (javoblar uchun)."""

    class Meta:
        model = User
        fields = (
            "id",
            "phone",
            "full_name",
            "role",
            "lang",
            "avatar",
            "is_verified",
        )


class MeUpdateSerializer(serializers.ModelSerializer):
    """'Mening profilim' tahriri — telefon va rol o'zgartirilmaydi."""

    class Meta:
        model = User
        fields = ("full_name", "lang", "avatar")
