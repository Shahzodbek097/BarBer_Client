"""Bosqich 2: User va OTPCode model testlari."""

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.factories import OTPCodeFactory, UserFactory
from apps.accounts.models import OTPPurpose, User

pytestmark = pytest.mark.django_db


class TestUserManager:
    def test_create_user_without_password_sets_unusable_password(self):
        user = User.objects.create_user("+9989011100011", "Ali")

        assert user.phone == "+9989011100011"
        assert user.full_name == "Ali"
        assert user.role == User.Role.CLIENT
        assert not user.has_usable_password()

    def test_create_user_with_password(self):
        user = User.objects.create_user("+9989011100012", "Vali", "parol-123")

        assert user.has_usable_password()
        assert user.check_password("parol-123")

    def test_create_user_strips_phone_whitespace(self):
        user = User.objects.create_user("  +9989011100013  ", "Ali")

        assert user.phone == "+9989011100013"

    def test_create_user_requires_phone(self):
        with pytest.raises(ValueError):
            User.objects.create_user("")

    def test_create_superuser_sets_all_flags(self):
        user = User.objects.create_superuser("+9989011100014", "Admin", "admin-parol")

        assert user.is_staff
        assert user.is_superuser
        assert user.role == User.Role.SUPERADMIN
        assert user.is_verified

    def test_phone_must_be_unique(self):
        User.objects.create_user("+9989011100015", "Bir")

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user("+9989011100015", "Ikki")


class TestUserModel:
    def test_factory_defaults(self):
        user = UserFactory()

        assert user.role == User.Role.CLIENT
        assert user.is_verified is False
        assert user.is_blocked is False
        assert user.lang == User.Lang.UZ
        assert user.is_active  # AbstractUser default

    def test_str_prefers_full_name(self):
        user = UserFactory(full_name="Jasur", phone="+9989011100016")

        assert str(user) == "Jasur"

    def test_str_falls_back_to_phone(self):
        user = UserFactory(full_name="", phone="+9989011100017")

        assert str(user) == "+9989011100017"

    def test_role_helpers(self):
        client = UserFactory(role=User.Role.CLIENT)
        barber = UserFactory(role=User.Role.BARBER)
        salon_admin = UserFactory(role=User.Role.SALON_ADMIN)

        assert client.is_client and not client.is_barber and not client.is_salon_admin
        assert barber.is_barber
        assert salon_admin.is_salon_admin


class TestOTPCode:
    def test_defaults(self):
        otp = OTPCodeFactory()

        assert otp.attempts == 0
        assert otp.is_used is False
        assert otp.expires_at > timezone.now()

    def test_str_shows_phone_and_purpose(self):
        otp = OTPCodeFactory(phone="+9989011100018")

        assert str(otp) == "+9989011100018 (login)"

    def test_purpose_choices(self):
        assert OTPPurpose.REGISTRATION == "registration"
        assert OTPPurpose.LOGIN == "login"
        assert OTPPurpose.PASSWORD_RESET == "password_reset"
