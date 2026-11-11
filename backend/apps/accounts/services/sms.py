"""SMS provayder adapterlari (TZ 6.1).

Plan qoidasi: tashqi tizimlar faqat adapter orqali — biznes logika
(`otp.py`) faqat `get_sms_client()` ni chaqiradi, provayder haqida bilmaydi.

Provayderlar:
- console — dev muhit: SMS logga yoziladi (haqiqiy xarajat yo'q)
- eskiz   — prod: https://notify.eskiz.uz (token email/parol orqali)
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

ESKIZ_BASE_URL = "https://notify.eskiz.uz/api"
ESKIZ_SENDER = "4546"


class SMSError(Exception):
    """SMS provayder xatosi."""


class BaseSMSClient:
    name = "base"

    def send(self, phone: str, message: str) -> None:
        raise NotImplementedError


class ConsoleSMSClient(BaseSMSClient):
    """Dev: SMS konsol/logga yoziladi."""

    name = "console"

    def send(self, phone: str, message: str) -> None:
        logger.info("[SMS console] %s -> %s", phone, message)


class EskizSMSClient(BaseSMSClient):
    """Eskiz.uz klient: avval token, keyin SMS."""

    name = "eskiz"
    timeout = 10

    def __init__(self) -> None:
        self._token: str | None = None

    def _auth_token(self) -> str:
        if self._token:
            return self._token

        email = settings.SMS_ESKIZ_EMAIL
        password = settings.SMS_ESKIZ_PASSWORD
        if not email or not password:
            raise SMSError("Eskiz uchun SMS_ESKIZ_EMAIL/PASSWORD .env da berilmagan.")

        response = requests.post(
            f"{ESKIZ_BASE_URL}/auth/login",
            json={"email": email, "password": password},
            timeout=self.timeout,
        )
        if response.status_code != 200:
            raise SMSError(f"Eskiz auth xato: HTTP {response.status_code}")
        self._token = response.json()["data"]["token"]
        return self._token

    def send(self, phone: str, message: str) -> None:
        token = self._auth_token()
        response = requests.post(
            f"{ESKIZ_BASE_URL}/message/sms/send",
            json={
                "mobile_phone": phone.lstrip("+"),
                "message": message,
                "from": ESKIZ_SENDER,
            },
            headers={"Authorization": f"Bearer {token}"},
            timeout=self.timeout,
        )
        if response.status_code != 200:
            raise SMSError(f"Eskiz send xato: HTTP {response.status_code}")
        logger.info("[SMS eskiz] %s -> yuborildi", phone)


_clients: dict[str, BaseSMSClient] = {}


def get_sms_client() -> BaseSMSClient:
    """Sozlamaga qarab provayder qaytaradi (SMS_PROVIDER: console|eskiz).

    Instance provayder nomi bo'yicha keshlanadi — Eskiz auth tokeni ham
    klient ichida keshlanadi (har SMS uchun qayta login bo'lmaydi).
    """
    provider = settings.SMS_PROVIDER
    if provider not in _clients:
        if provider == "eskiz":
            _clients[provider] = EskizSMSClient()
        else:
            _clients[provider] = ConsoleSMSClient()
    return _clients[provider]
