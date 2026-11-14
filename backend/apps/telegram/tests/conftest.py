"""Telegram testlar uchun fixture'lar."""

import pytest


@pytest.fixture
def fake_bot(monkeypatch):
    """Bot adapter o'rniga yozuvchi soxta klient.

    Qaytaradi: yuborilgan xabarlar ro'yxati [{"chat_id", "text"}, ...].
    """
    sent: list[dict] = []

    class FakeBot:
        name = "fake"

        def send_message(self, chat_id: int, text: str) -> None:
            sent.append({"chat_id": chat_id, "text": text})

    fake = FakeBot()
    monkeypatch.setattr("apps.telegram.services.notifier.get_bot", lambda: fake)
    monkeypatch.setattr("apps.telegram.webhook.get_bot", lambda: fake)
    return sent


@pytest.fixture
def fake_reminder_sms(monkeypatch):
    """Eslatma SMS fallback'ini ushlab turuvchi soxta klient."""
    sent: list[dict] = []

    class FakeSMSClient:
        name = "fake"

        def send(self, phone: str, message: str) -> None:
            sent.append({"phone": phone, "message": message})

    monkeypatch.setattr("apps.telegram.services.reminders.get_sms_client", lambda: FakeSMSClient())
    return sent
