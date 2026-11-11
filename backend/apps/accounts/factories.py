"""Foydalanuvchi va OTP factory'lari.

UserFactory parolsiz yaratadi (OTP oqimi). Parol talab qiladigan testlarda
`user.set_password(...)` chaqiriladi yoki `password=factory.django.Password(...)`
beriladi.
"""

from datetime import timedelta

import factory
from django.utils import timezone

from apps.accounts.models import OTPCode, OTPPurpose, User


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ("phone",)

    phone = factory.Sequence(lambda n: f"+99890123{n:04d}")
    full_name = factory.Sequence(lambda n: f"Foydalanuvchi {n + 1}")
    role = User.Role.CLIENT
    lang = User.Lang.UZ


class OTPCodeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OTPCode

    phone = factory.Sequence(lambda n: f"+99890123{n:04d}")
    code_hash = factory.Sequence(lambda n: f"{n:x}".rjust(64, "0"))
    purpose = OTPPurpose.LOGIN
    expires_at = factory.LazyFunction(lambda: timezone.now() + timedelta(minutes=5))
