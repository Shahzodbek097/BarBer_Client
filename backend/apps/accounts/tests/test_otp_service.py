"""Bosqich 3: OTP servis testlari (yuborish/tekshirish va rate-limitlar)."""

from datetime import timedelta

import pytest
from conftest import extract_code
from django.utils import timezone

from apps.accounts.factories import UserFactory
from apps.accounts.models import OTPCode, OTPPurpose
from apps.accounts.services import otp as otp_service
from apps.accounts.services.exceptions import (
    OTPCooldown,
    OTPExpired,
    OTPHourlyLimit,
    OTPInvalid,
    OTPMaxAttempts,
    OTPNotFound,
)

pytestmark = pytest.mark.django_db

PHONE = "+998901234567"


def _age_last_otp(seconds: int) -> None:
    """So'nggi OTP'ning created_at sanasini orqaga suradi (auto_now_add bypass)."""
    old = timezone.now() - timedelta(seconds=seconds)
    OTPCode.objects.update(created_at=old)


class TestSendOTP:
    def test_creates_code_and_sends_sms(self, fake_sms):
        code = otp_service.send_otp(PHONE, OTPPurpose.LOGIN)

        assert len(code) == 5 and code.isdigit()
        assert len(fake_sms) == 1
        assert fake_sms[0]["phone"] == PHONE
        assert code in fake_sms[0]["message"]

        otp = OTPCode.objects.get(phone=PHONE)
        assert otp.purpose == OTPPurpose.LOGIN
        assert otp.code_hash != code  # bazada plaintext emas
        assert len(otp.code_hash) == 64  # sha256 hex

    def test_code_is_sha256_hash(self, fake_sms):
        import hashlib

        code = otp_service.send_otp(PHONE, OTPPurpose.REGISTRATION)
        otp = OTPCode.objects.get(phone=PHONE)

        assert otp.code_hash == hashlib.sha256(code.encode()).hexdigest()

    def test_cooldown_blocks_immediate_resend(self, fake_sms):
        otp_service.send_otp(PHONE, OTPPurpose.LOGIN)

        with pytest.raises(OTPCooldown):
            otp_service.send_otp(PHONE, OTPPurpose.LOGIN)

    def test_cooldown_allows_after_window(self, fake_sms):
        otp_service.send_otp(PHONE, OTPPurpose.LOGIN)
        _age_last_otp(seconds=61)  # cooldown 60s

        code = otp_service.send_otp(PHONE, OTPPurpose.LOGIN)

        assert len(fake_sms) == 2
        assert code != extract_code(fake_sms[0]["message"])

    def test_cooldown_separate_per_purpose(self, fake_sms):
        otp_service.send_otp(PHONE, OTPPurpose.REGISTRATION)

        # boshqa maqsudga cooldown ta'sir qilmaydi
        otp_service.send_otp(PHONE, OTPPurpose.LOGIN)

        assert len(fake_sms) == 2

    def test_hourly_limit_blocks(self, fake_sms):
        for _ in range(5):
            otp_service.send_otp(PHONE, OTPPurpose.LOGIN)
            _age_last_otp(seconds=61)

        with pytest.raises(OTPHourlyLimit):
            otp_service.send_otp(PHONE, OTPPurpose.LOGIN)

    def test_hourly_limit_ignores_old_codes(self, fake_sms):
        for _ in range(5):
            otp_service.send_otp(PHONE, OTPPurpose.LOGIN)
            _age_last_otp(seconds=61)

        _age_last_otp(seconds=3700)  # 5 tasi ham 1 soatdan eski

        otp_service.send_otp(PHONE, OTPPurpose.LOGIN)  # limit yana ochiq

        assert len(fake_sms) == 6


class TestVerifyOTP:
    def test_success_verifies_user_and_consumes_code(self, fake_sms):
        user = UserFactory(phone=PHONE)
        code = otp_service.send_otp(PHONE, OTPPurpose.LOGIN)

        result = otp_service.verify_otp(PHONE, OTPPurpose.LOGIN, code)

        assert result == user
        user.refresh_from_db()
        assert user.is_verified is True

        otp = OTPCode.objects.get(phone=PHONE)
        assert otp.is_used is True

    def test_wrong_code_increments_attempts(self, fake_sms):
        UserFactory(phone=PHONE)
        otp_service.send_otp(PHONE, OTPPurpose.LOGIN)

        with pytest.raises(OTPInvalid):
            otp_service.verify_otp(PHONE, OTPPurpose.LOGIN, "00000")

        otp = OTPCode.objects.get(phone=PHONE)
        assert otp.attempts == 1
        assert otp.is_used is False

    def test_max_attempts_blocks_correct_code(self, fake_sms):
        UserFactory(phone=PHONE)
        code = otp_service.send_otp(PHONE, OTPPurpose.LOGIN)

        # 2 xato urinish: har safar "N urinish qoldi"
        for _ in range(2):
            with pytest.raises(OTPInvalid):
                otp_service.verify_otp(PHONE, OTPPurpose.LOGIN, "00000")

        # 3-xato urinishda limit tugaydi
        with pytest.raises(OTPMaxAttempts):
            otp_service.verify_otp(PHONE, OTPPurpose.LOGIN, "00000")

        # to'g'ri kod ham endi qabul qilinmaydi
        with pytest.raises(OTPMaxAttempts):
            otp_service.verify_otp(PHONE, OTPPurpose.LOGIN, code)

    def test_expired_code_rejected(self, fake_sms):
        UserFactory(phone=PHONE)
        code = otp_service.send_otp(PHONE, OTPPurpose.LOGIN)

        expired = timezone.now() - timedelta(seconds=1)
        OTPCode.objects.update(expires_at=expired)

        with pytest.raises(OTPExpired):
            otp_service.verify_otp(PHONE, OTPPurpose.LOGIN, code)

    def test_verify_without_send_raises_not_found(self):
        with pytest.raises(OTPNotFound):
            otp_service.verify_otp(PHONE, OTPPurpose.LOGIN, "12345")

    def test_blocked_user_rejected_after_valid_code(self, fake_sms):
        UserFactory(phone=PHONE, is_blocked=True)
        code = otp_service.send_otp(PHONE, OTPPurpose.LOGIN)

        from django.core.exceptions import PermissionDenied

        with pytest.raises(PermissionDenied):
            otp_service.verify_otp(PHONE, OTPPurpose.LOGIN, code)

    def test_whitespace_in_code_stripped(self, fake_sms):
        UserFactory(phone=PHONE)
        code = otp_service.send_otp(PHONE, OTPPurpose.LOGIN)

        result = otp_service.verify_otp(PHONE, OTPPurpose.LOGIN, f" {code} ")

        assert result.phone == PHONE
