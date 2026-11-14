"""Telegram Bot API adapterlari (plan qoidasi: tashqi tizim adapter orqali).

Provayderlar:
- console — dev/test: xabar logga yoziladi (TELEGRAM_BOT_TOKEN bo'sh)
- http    — prod: https://api.telegram.org/bot<token>/sendMessage
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"


class TelegramError(Exception):
    """Telegram API xatosi."""


class BaseBot:
    name = "base"

    def send_message(self, chat_id: int, text: str) -> None:
        raise NotImplementedError


class ConsoleBot(BaseBot):
    """Dev: xabar konsol/logga yoziladi."""

    name = "console"

    def send_message(self, chat_id: int, text: str) -> None:
        logger.info("[Telegram console] chat=%s text=%r", chat_id, text)


class HttpBot(BaseBot):
    """Haqiqiy Bot API klient (sendMessage)."""

    name = "http"
    timeout = 10

    def send_message(self, chat_id: int, text: str) -> None:
        token = settings.TELEGRAM_BOT_TOKEN
        if not token:
            raise TelegramError("TELEGRAM_BOT_TOKEN berilmagan.")
        response = requests.post(
            f"{TELEGRAM_API}/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=self.timeout,
        )
        if response.status_code != 200:
            raise TelegramError(f"Telegram send xato: HTTP {response.status_code}")
        logger.info("[Telegram http] chat=%s -> yuborildi", chat_id)


_bots: dict[str, BaseBot] = {}


def get_bot() -> BaseBot:
    """Token bor-yo'qligiga qarab klient (nomi bo'yicha keshlanadi)."""
    provider = "http" if settings.TELEGRAM_BOT_TOKEN else "console"
    if provider not in _bots:
        _bots[provider] = HttpBot() if provider == "http" else ConsoleBot()
    return _bots[provider]
