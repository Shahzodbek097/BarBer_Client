"""Telegram bog'lanish API (kabinetlar uchun).

GET  — holat (bog'langan chat ma'lumoti)
POST — yangi bir martalik ulanish kodi
"""

from django.conf import settings
from rest_framework import status as http_status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.telegram.models import TelegramChat
from apps.telegram.services.linking import create_link_code


class TelegramLinkView(APIView):
    """Chat bog'lash: holat ko'rish va kod olish."""

    def get(self, request) -> Response:
        chat = TelegramChat.objects.filter(user=request.user).first()
        data = {
            "linked": bool(chat and chat.is_active),
            "bot_username": settings.TELEGRAM_BOT_USERNAME,
        }
        if chat:
            data.update(
                {
                    "chat_id": chat.chat_id,
                    "username": chat.username,
                    "linked_at": chat.linked_at,
                }
            )
        return Response(data)

    def post(self, request) -> Response:
        code = create_link_code(request.user)
        return Response(
            {"code": code.code, "expires_at": code.expires_at},
            status=http_status.HTTP_201_CREATED,
        )
