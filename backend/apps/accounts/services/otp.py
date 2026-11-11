"""OTP: yaratish, yuborish va tekshirish.

Xavfsizlik qoidalari (TZ 6.1):
- kod bazada faqat sha256 hash ko'rinishida saqlanadi
- bir kod 3 marta xato kiritilsa bloklanadi (MAX_ATTEMPTS)
- bir telefon+maqsad uchun qayta yuborish 60s dam bilan (RESEND_COOLDOWN)
- bir telefon soatiga 5 tadan ko'p kod olmaydi (HOURLY_LIMIT)
"""

import hashlib
import hmac
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from apps.accounts.models import OTPCode, User
from apps.accounts.services.exceptions import (
    OTPCooldown,
    OTPExpired,
    OTPHourlyLimit,
    OTPInvalid,
    OTPMaxAttempts,
    OTPNotFound,
)
from apps.accounts.services.sms import get_sms_client
from apps.core.services.audit import log_action


def _generate_code() -> str:
    length = settings.OTP_CONFIG["LENGTH"]
    return f"{secrets.randbelow(10**length):0{length}d}"


def _hash(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def _message(code: str) -> str:
    minutes = settings.OTP_CONFIG["LIFETIME_SECONDS"] // 60
    return f"BarBer_Client tasdiqlash kodi: {code}. Amal qilish muddati {minutes} daqiqa."


def send_otp(phone: str, purpose: str) -> str:
    """Yangi OTP yaratadi va SMS yuboradi.

    Qaytaradi: kod matni (faqat debug uchun — API javobida hech qachon
    DEBUG'dan tashqari ko'rsatilmaydi).
    """
    phone = phone.strip()
    now = timezone.now()

    hourly = OTPCode.objects.filter(phone=phone, created_at__gte=now - timedelta(hours=1)).count()
    if hourly >= settings.OTP_CONFIG["HOURLY_LIMIT"]:
        raise OTPHourlyLimit()

    last = OTPCode.objects.filter(phone=phone, purpose=purpose).order_by("-created_at").first()
    if last and last.created_at > now - timedelta(
        seconds=settings.OTP_CONFIG["RESEND_COOLDOWN_SECONDS"]
    ):
        raise OTPCooldown()

    code = _generate_code()
    OTPCode.objects.create(
        phone=phone,
        code_hash=_hash(code),
        purpose=purpose,
        expires_at=now + timedelta(seconds=settings.OTP_CONFIG["LIFETIME_SECONDS"]),
    )

    get_sms_client().send(phone, _message(code))
    return code


def verify_otp(phone: str, purpose: str, code: str) -> User:
    """Kodni tekshiradi; muvaffaqiyatda user'ni qaytaradi (is_verified=True)."""
    phone = phone.strip()
    code = code.strip()

    otp = (
        OTPCode.objects.filter(phone=phone, purpose=purpose, is_used=False)
        .order_by("-created_at")
        .first()
    )
    if otp is None:
        raise OTPNotFound()
    if otp.expires_at < timezone.now():
        raise OTPExpired()
    if otp.attempts >= settings.OTP_CONFIG["MAX_ATTEMPTS"]:
        raise OTPMaxAttempts()

    if not hmac.compare_digest(otp.code_hash, _hash(code)):
        otp.attempts += 1
        otp.save(update_fields=("attempts",))
        left = settings.OTP_CONFIG["MAX_ATTEMPTS"] - otp.attempts
        if left <= 0:
            raise OTPMaxAttempts()
        raise OTPInvalid(detail=f"Kod xato. {left} ta urinish qoldi.")

    otp.is_used = True
    otp.save(update_fields=("is_used",))

    user = User.objects.filter(phone=phone).first()
    if user is None:
        raise OTPNotFound(detail="Foydalanuvchi topilmadi.")
    if user.is_blocked or not user.is_active:
        raise PermissionDenied("Foydalanuvchi bloklangan.")

    if not user.is_verified:
        user.is_verified = True
        user.save(update_fields=("is_verified",))

    log_action(
        actor=user,
        action=f"otp_verified_{purpose}",
        model_name="accounts.User",
        object_id=user.pk,
    )
    return user
