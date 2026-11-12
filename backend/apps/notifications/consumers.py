"""WebSocket consumer: JWT (?token=) bilan auth, `user_{id}` guruhiga qo'shiladi.

Marshrutlar (config/asgi.py):
- /ws/client/{user_id}/  — mijoz javob push (confirm/reject/propose/...)
- /ws/barber/{user_id}/  — sartarosh yangi so'rov push

Auth: brauzer WS'da header yubora olmaydi — access JWT `?token=`
query parametri bilan uzatiladi. Token yaroqsiz yoki {user_id} mos
kelmasa ulanish darhol yopiladi.
"""

import json
from urllib.parse import parse_qs

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import UntypedToken


class NotifyConsumer(WebsocketConsumer):
    """Bir yo'nalishli xabarnoma kanali (server → klient)."""

    def connect(self) -> None:
        query = parse_qs(self.scope["query_string"].decode())
        token = (query.get("token") or [None])[0]

        if not self._authorize(token):
            self.close()
            return

        self.group_name = f"user_{self.url_user_id}"
        async_to_sync(self.channel_layer.group_add)(self.group_name, self.channel_name)
        self.accept()

    def disconnect(self, code) -> None:
        if hasattr(self, "group_name"):
            async_to_sync(self.channel_layer.group_discard)(self.group_name, self.channel_name)

    def _authorize(self, token: str | None) -> bool:
        """Token imzosini va {user_id} mosligini tekshiradi."""
        try:
            payload = UntypedToken(token).payload
        except (TokenError, TypeError):
            return False

        self.url_user_id = self.scope["url_route"]["kwargs"]["user_id"]
        if str(self.url_user_id) != str(payload.get("user_id")):
            return False
        return True

    def notify_event(self, event: dict) -> None:
        """Group_send `{type: "notify.event"}` handleri — klientga JSON."""
        self.send(text_data=json.dumps(event["payload"], ensure_ascii=False))
