"""Chat bog'lash oqimi: kabinetda kod olish → botga `/start KOD` yuborish."""

import secrets
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.accounts.models import User
from apps.telegram.models import LinkCode, TelegramChat


class TelegramLinkError(Exception):
    """Kod yaroqsiz / muddati tugagan / ishlatilgan."""


def generate_code() -> str:
    """6 xonali kod (takrorlanmas — bazada qidirib ko'riladi)."""
    while True:
        code = f"{secrets.randbelow(1_000_000):06d}"
        if not LinkCode.objects.filter(code=code).exists():
            return code


def create_link_code(user: User) -> LinkCode:
    """Yangi kod yaratadi (oldingi ishlatilmaganlarni bekor qilib)."""
    LinkCode.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())
    return LinkCode.objects.create(
        user=user,
        code=generate_code(),
        expires_at=timezone.now() + timedelta(seconds=settings.TELEGRAM_LINK_TTL),
    )


def link_chat(code: str, chat_id: int, username: str = "") -> User:
    """Kod bo'yicha chatni bog'laydi; foydalanuvchini qaytaradi."""
    try:
        link = LinkCode.objects.select_related("user").get(code=code)
    except LinkCode.DoesNotExist as exc:
        raise TelegramLinkError("Kod topilmadi. Kabinetdan yangi kod oling.") from exc

    if link.used_at is not None:
        raise TelegramLinkError("Bu kod allaqachon ishlatilgan.")
    if link.expires_at <= timezone.now():
        raise TelegramLinkError("Kod muddati tugagan. Yangi kod oling.")

    link.used_at = timezone.now()
    link.save(update_fields=["used_at"])

    TelegramChat.objects.update_or_create(
        user=link.user,
        defaults={"chat_id": chat_id, "username": username or "", "is_active": True},
    )
    return link.user
