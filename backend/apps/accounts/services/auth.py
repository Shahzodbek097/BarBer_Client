"""Ro'yxatdan o'tish, kirish va JWT chiqarish (bosqich 3).

Eslatma: register faqat User yaratadi — BarberProfile/Salon profillari
 tegishli app'larda (bosqich 4/5 onboarding) to'ldiriladi. Bu
importlar faqat yuqoriga qoidasiga muvofiq (accounts pastki app'larni
bilmaydi).
"""

from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import OTPPurpose, User
from apps.accounts.services import otp
from apps.accounts.services.exceptions import PermissionDenied, PhoneNotRegistered
from apps.core.services.audit import log_action


def register_user(phone: str, full_name: str, role: str) -> tuple[User, str]:
    """Yangi user yaratadi va tasdiqlash OTP'sini yuboradi.

    Qaytaradi: (user, kod) — kod faqat DEBUG javobida ko'rsatiladi.
    """
    user = User.objects.create_user(phone=phone, full_name=full_name, role=role)
    code = otp.send_otp(phone, OTPPurpose.REGISTRATION)

    log_action(
        actor=user,
        action="user_registered",
        model_name="accounts.User",
        object_id=user.pk,
        payload={"role": role},
    )
    return user, code


def send_login_otp(phone: str) -> str:
    """Mavjud, faol user uchun kirish OTP'sini yuboradi."""
    user = User.objects.filter(phone=phone.strip()).first()
    if user is None:
        raise PhoneNotRegistered()
    if user.is_blocked or not user.is_active:
        raise PermissionDenied("Foydalanuvchi bloklangan.")

    return otp.send_otp(phone, OTPPurpose.LOGIN)


def issue_tokens(user: User) -> dict:
    """Access/refresh juftligini qaytaradi (rotation + blacklist yoqilgan)."""
    refresh = RefreshToken.for_user(user)
    return {"refresh": str(refresh), "access": str(refresh.access_token)}
