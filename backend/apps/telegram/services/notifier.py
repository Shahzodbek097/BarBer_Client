"""Notification → Telegram ko'prik (faqat bog'langan chat bo'lsa).

Hech qachon asosiy oqimni buzmaydi: xatolar faqat logga.
"""

import logging

from apps.accounts.models import User
from apps.telegram.models import TelegramChat
from apps.telegram.services.bot import get_bot

logger = logging.getLogger(__name__)


def send_to_user(user: User, title: str, body: str = "") -> bool:
    """Chat bog'langan bo'lsa xabar yuboradi. True — yuborildi."""
    try:
        chat = TelegramChat.objects.filter(user=user, is_active=True).only("chat_id").first()
    except Exception:  # noqa: BLE001
        return False
    if not chat:
        return False

    text = f"💈 <b>{title}</b>" + (f"\n{body}" if body else "")
    try:
        get_bot().send_message(chat.chat_id, text)
    except Exception:  # noqa: BLE001 — telegram muhim oqimni buzmasligi kerak
        logger.warning("Telegram push muvaffaqiyatsiz (user=%s)", user.pk, exc_info=True)
        return False
    return True
