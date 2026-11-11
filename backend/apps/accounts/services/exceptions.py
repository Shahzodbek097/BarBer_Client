"""Auth/OTP servis xatolari.

APIException'dan meros olgani uchun DRF handler tomonidan JSON xatoga
aylanadi (masalan, OTPCooldown -> 429 {"detail": ...}).
"""

from django.core.exceptions import PermissionDenied
from rest_framework.exceptions import APIException


class OTPError(APIException):
    status_code = 400


class OTPCooldown(OTPError):
    status_code = 429
    default_detail = "Yangi kod so'rash uchun biroz kutib turing."
    default_code = "otp_cooldown"


class OTPHourlyLimit(OTPError):
    status_code = 429
    default_detail = "Kod so'rash limiti to'ldi. Bir soatdan keyin urinib ko'ring."
    default_code = "otp_hourly_limit"


class OTPExpired(OTPError):
    default_detail = "Kod muddati tugagan. Yangi kod so'rang."
    default_code = "otp_expired"


class OTPMaxAttempts(OTPError):
    default_detail = "Noto'g'ri kod juda ko'p kiritildi. Yangi kod so'rang."
    default_code = "otp_max_attempts"


class OTPInvalid(OTPError):
    default_detail = "Kod xato."
    default_code = "otp_invalid"


class OTPNotFound(OTPError):
    default_detail = "Kod topilmadi. Avval kod so'rang."
    default_code = "otp_not_found"


class PhoneNotRegistered(APIException):
    status_code = 400
    default_detail = "Bu raqam ro'yxatdan o'tmagan."
    default_code = "phone_not_registered"


# Django PermissionDenied -> DRF 403 ga aylanadi
__all__ = [  # noqa: RUF022
    "OTPError",
    "OTPCooldown",
    "OTPHourlyLimit",
    "OTPExpired",
    "OTPMaxAttempts",
    "OTPInvalid",
    "OTPNotFound",
    "PhoneNotRegistered",
    "PermissionDenied",
]
