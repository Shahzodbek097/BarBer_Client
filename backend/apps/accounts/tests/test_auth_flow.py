"""Bosqich 3: auth API oqim testlari (register -> OTP -> JWT -> me/logout)."""

from datetime import timedelta

import pytest
from conftest import extract_code
from django.test import override_settings
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.factories import UserFactory
from apps.accounts.models import User
from apps.core.models import AuditLog

pytestmark = pytest.mark.django_db

PHONE = "+998901112233"
REGISTER_DATA = {"phone": PHONE, "full_name": "Test Mijoz", "role": "client"}


class TestRegister:
    def test_creates_user_and_sends_otp(self, api_client, fake_sms):
        response = api_client.post("/api/v1/auth/register/", REGISTER_DATA)

        assert response.status_code == 201
        user = User.objects.get(phone=PHONE)
        assert user.role == User.Role.CLIENT
        assert user.is_verified is False
        assert len(fake_sms) == 1 and fake_sms[0]["phone"] == PHONE
        assert "debug_code" not in response.json()  # DEBUG=False

    def test_audit_log_written(self, api_client, fake_sms):
        api_client.post("/api/v1/auth/register/", REGISTER_DATA)

        assert AuditLog.objects.filter(action="user_registered").exists()

    def test_duplicate_phone_rejected(self, api_client, fake_sms):
        UserFactory(phone=PHONE)

        response = api_client.post("/api/v1/auth/register/", REGISTER_DATA)

        assert response.status_code == 400
        assert "phone" in response.json()

    def test_superadmin_role_rejected(self, api_client, fake_sms):
        data = {**REGISTER_DATA, "role": "superadmin"}

        response = api_client.post("/api/v1/auth/register/", data)

        assert response.status_code == 400

    def test_invalid_phone_rejected(self, api_client, fake_sms):
        data = {**REGISTER_DATA, "phone": "998901112233"}  # + belgisi yo'q

        response = api_client.post("/api/v1/auth/register/", data)

        assert response.status_code == 400

    @override_settings(DEBUG=True)
    def test_debug_code_in_response_in_dev(self, api_client, fake_sms):
        response = api_client.post("/api/v1/auth/register/", REGISTER_DATA)

        assert response.json()["debug_code"] == extract_code(fake_sms[0]["message"])


class TestLogin:
    def test_sends_login_otp(self, api_client, fake_sms):
        UserFactory(phone=PHONE)

        response = api_client.post("/api/v1/auth/login/", {"phone": PHONE})

        assert response.status_code == 200
        assert fake_sms[0]["phone"] == PHONE

    def test_unknown_phone_rejected(self, api_client, fake_sms):
        response = api_client.post("/api/v1/auth/login/", {"phone": PHONE})

        assert response.status_code == 400
        assert "ro'yxatdan o'tmagan" in response.json()["detail"]

    def test_blocked_user_forbidden(self, api_client, fake_sms):
        UserFactory(phone=PHONE, is_blocked=True)

        response = api_client.post("/api/v1/auth/login/", {"phone": PHONE})

        assert response.status_code == 403


class TestVerifyOTP:
    def _register_and_get_code(self, api_client, fake_sms):
        api_client.post("/api/v1/auth/register/", REGISTER_DATA)
        return extract_code(fake_sms[0]["message"])

    def test_full_flow_returns_tokens(self, api_client, fake_sms):
        code = self._register_and_get_code(api_client, fake_sms)

        response = api_client.post(
            "/api/v1/auth/verify-otp/",
            {"phone": PHONE, "purpose": "registration", "code": code},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["access"] and data["refresh"]
        assert data["user"]["phone"] == PHONE
        assert data["user"]["is_verified"] is True

    def test_wrong_code_then_correct(self, api_client, fake_sms):
        code = self._register_and_get_code(api_client, fake_sms)

        bad = api_client.post(
            "/api/v1/auth/verify-otp/",
            {"phone": PHONE, "purpose": "registration", "code": "00000"},
        )
        good = api_client.post(
            "/api/v1/auth/verify-otp/",
            {"phone": PHONE, "purpose": "registration", "code": code},
        )

        assert bad.status_code == 400
        assert "urinish qoldi" in bad.json()["detail"]
        assert good.status_code == 200

    def test_expired_code_rejected(self, api_client, fake_sms):
        self._register_and_get_code(api_client, fake_sms)

        from apps.accounts.models import OTPCode

        OTPCode.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        response = api_client.post(
            "/api/v1/auth/verify-otp/",
            {"phone": PHONE, "purpose": "registration", "code": "12345"},
        )

        assert response.status_code == 400

    def test_verify_without_otp_rejected(self, api_client, fake_sms):
        response = api_client.post(
            "/api/v1/auth/verify-otp/",
            {"phone": PHONE, "purpose": "registration", "code": "12345"},
        )

        assert response.status_code == 400

    def test_blocked_user_gets_403_on_verify(self, api_client, fake_sms):
        user = UserFactory(phone=PHONE)
        api_client.post("/api/v1/auth/login/", {"phone": PHONE})
        code = extract_code(fake_sms[0]["message"])

        # kod olgandan keyin bloklandi
        user.is_blocked = True
        user.save(update_fields=("is_blocked",))

        response = api_client.post(
            "/api/v1/auth/verify-otp/",
            {"phone": PHONE, "purpose": "login", "code": code},
        )

        assert response.status_code == 403


class TestMe:
    def test_requires_auth(self, api_client):
        response = api_client.get("/api/v1/auth/me/")

        assert response.status_code == 401

    def test_returns_profile(self, api_client, make_auth_client):
        user = UserFactory(is_verified=True)

        response = make_auth_client(user).get("/api/v1/auth/me/")

        assert response.status_code == 200
        assert response.json()["phone"] == user.phone
        assert response.json()["role"] == "client"

    def test_patch_updates_lang(self, api_client, make_auth_client):
        user = UserFactory()

        response = make_auth_client(user).patch("/api/v1/auth/me/", {"lang": "ru"})

        assert response.status_code == 200
        user.refresh_from_db()
        assert user.lang == User.Lang.RU


class TestThrottle:
    def test_verify_rate_limited(self, api_client, fake_sms):
        """DRF throttle ishlashi: otp_verify 2/min -> 3-so'rov 429.

        Eslatma: DRF THROTTLE_RATES'ni modul import paytida snapshot qiladi,
        shuning uchun klass attr'ini to'g'ridan-to'g'ri patch qilamiz.
        """
        from unittest.mock import patch

        from django.core.cache import cache
        from rest_framework.throttling import SimpleRateThrottle

        payload = {"phone": PHONE, "purpose": "registration", "code": "00000"}
        with patch.dict(SimpleRateThrottle.THROTTLE_RATES, {"otp_verify": "2/min"}):
            cache.clear()
            responses = [api_client.post("/api/v1/auth/verify-otp/", payload) for _ in range(3)]

        assert responses[0].status_code == 400  # OTPNotFound — throttle baribir hisoblaydi
        assert responses[2].status_code == 429


class TestRefreshLogout:
    def test_refresh_rotates_and_blacklists_old(self, api_client):
        user = UserFactory()
        refresh = RefreshToken.for_user(user)

        first = api_client.post("/api/v1/auth/refresh/", {"refresh": str(refresh)})
        assert first.status_code == 200
        new_refresh = first.json()["refresh"]
        assert new_refresh != str(refresh)  # rotation

        # eski refresh blacklist'ga tushgan
        second = api_client.post("/api/v1/auth/refresh/", {"refresh": str(refresh)})
        assert second.status_code == 401

    def test_refresh_blocked_user_forbidden(self, api_client):
        user = UserFactory()
        refresh = RefreshToken.for_user(user)
        user.is_blocked = True
        user.save(update_fields=("is_blocked",))

        response = api_client.post("/api/v1/auth/refresh/", {"refresh": str(refresh)})

        assert response.status_code == 403

    def test_logout_blacklists_refresh(self, api_client, make_auth_client):
        user = UserFactory()
        refresh = RefreshToken.for_user(user)

        response = make_auth_client(user).post("/api/v1/auth/logout/", {"refresh": str(refresh)})
        assert response.status_code == 200, response.json()

        after = api_client.post("/api/v1/auth/refresh/", {"refresh": str(refresh)})
        assert after.status_code == 401
        assert BlacklistedToken.objects.count() == 1

    def test_logout_rejects_foreign_token(self, api_client, make_auth_client):
        stranger = UserFactory(phone="+9989012999999")
        foreign_refresh = RefreshToken.for_user(stranger)

        response = make_auth_client(UserFactory()).post(
            "/api/v1/auth/logout/", {"refresh": str(foreign_refresh)}
        )

        assert response.status_code == 403
        assert BlacklistedToken.objects.count() == 0
