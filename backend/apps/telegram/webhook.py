"""Telegram webhook (Bot API → biz).

Xavfsizlik: Telegram `X-Telegram-Bot-Api-Secret-Token` sarlavhasini
yuboradi — `TELEGRAM_WEBHOOK_SECRET` bilan solishtiriladi (bo'sh yoki
mos kelmasa 403). Qo'lda sozlash: `setWebhook` URL'ga secret qo'shiladi.
"""

import json
import logging

from django.conf import settings
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.telegram.services import linking
from apps.telegram.services.bot import get_bot

logger = logging.getLogger(__name__)

HELP_TEXT = (
    "BarBer navbat botiga xush kelibsiz! 👋\n"
    "Chatni bog'lash: veb-kabinetdan 'Telegram'ga ulanish' bo'limida kod "
    "oling va bu yerga /start KOD ko'rinishida yuboring."
)


def handle_update(update: dict) -> str | None:
    """Bir update'ni qayta ishlaydi; botga yuboriladigan javob qaytaradi."""
    message = update.get("message") or {}
    chat = message.get("chat") or {}
    text = (message.get("text") or "").strip()
    chat_id = chat.get("id")
    if chat_id is None or not text:
        return None

    parts = text.split()
    if parts[0].startswith("/start") and len(parts) > 1:
        try:
            user = linking.link_chat(parts[1], int(chat_id), chat.get("username") or "")
        except linking.TelegramLinkError as exc:
            return f"❌ {exc}"
        return f"✅ Ulashdi, {user.full_name}! Endi navbat holati va eslatmalari shu chatga keladi."
    if parts[0].startswith("/start"):
        return "Kod bilan: /start KOD (kodni veb-kabinetdan oling)."
    return HELP_TEXT


@require_POST
@csrf_exempt
def telegram_webhook(request, secret: str) -> JsonResponse:
    if not settings.TELEGRAM_WEBHOOK_SECRET or secret != settings.TELEGRAM_WEBHOOK_SECRET:
        return HttpResponseForbidden("wrong secret")
    try:
        update = json.loads(request.body.decode("utf-8") or "{}")
        reply = handle_update(update)
    except (ValueError, TypeError, KeyError):
        logger.warning("Webhook update o'qilmadi", exc_info=True)
        reply = None

    if reply:
        message = (update.get("message") or {}).get("chat") or {}
        chat_id = message.get("id")
        if chat_id is not None:
            try:
                get_bot().send_message(int(chat_id), reply)
            except Exception:  # noqa: BLE001 — webhook har doim 200 qaytarsin
                logger.warning("Webhook javob yuborilmadi", exc_info=True)
    return JsonResponse({"ok": True})
