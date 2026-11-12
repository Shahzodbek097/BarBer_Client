"""Xabarnoma emitteri: DB yozuvi + WebSocket push.

Plan qoidasi: tashqi tizim (channel layer) adapter orqali — bu yerda
yagona kirish nuqtasi `notify()`. Har ikkala operatsiya hech qachon
asosiy oqimni (navbat tsikli) buzmasligi kerak — xatolar faqat logga.
"""

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from apps.notifications.models import Notification

logger = logging.getLogger(__name__)


def push_to_user(user_id: int, payload: dict) -> None:
    """`user_{id}` WS guruhiga push (xato — faqat log)."""
    try:
        layer = get_channel_layer()
        if layer is None:
            return
        async_to_sync(layer.group_send)(
            f"user_{user_id}", {"type": "notify.event", "payload": payload}
        )
    except Exception:  # noqa: BLE001 — push muhim oqimni buzmasligi kerak
        logger.warning("WS push muvaffaqiyatsiz (user_id=%s)", user_id, exc_info=True)


def notify(recipient, ntype: str, title: str, body: str = "", link: str = "") -> None:
    """Xabarnoma yaratadi (DB) va WS orqali push qiladi."""
    try:
        notification = Notification.objects.create(
            recipient=recipient, type=ntype, title=title, body=body, link=link
        )
    except Exception:  # noqa: BLE001
        logger.warning("Xabarnoma yozilmadi (%s)", title, exc_info=True)
        return

    push_to_user(
        notification.recipient_id,
        {
            "id": notification.id,
            "type": ntype,
            "title": title,
            "body": body,
            "link": link,
            "created_at": notification.created_at.isoformat(),
        },
    )
