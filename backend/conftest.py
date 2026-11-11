"""Umumiy pytest fixture'lar (bosqich 3: auth testlari uchun kengaytirildi)."""

import re

import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    """DRF API klient (auth'siz)."""
    return APIClient()


@pytest.fixture
def fake_sms(monkeypatch):
    """SMS adapter o'rniga kodlarni ushlab turuvchi soxta klient.

    Qaytaradi: yuborilgan SMS ro'yxati [{"phone", "message"}, ...].
    """

    sent: list[dict] = []

    class FakeSMSClient:
        name = "fake"

        def send(self, phone: str, message: str) -> None:
            sent.append({"phone": phone, "message": message})

    monkeypatch.setattr("apps.accounts.services.otp.get_sms_client", lambda: FakeSMSClient())
    return sent


def extract_code(message: str) -> str:
    """SMS matnidan 5 xonali kodni ajratadi."""
    match = re.search(r"\b(\d{5})\b", message)
    assert match, f"SMS matnida kod topilmadi: {message}"
    return match.group(1)


@pytest.fixture
def make_auth_client(api_client):
    """Berilgan user uchun JWT bilan autentifikatsiyalangan klient qaytaradi."""

    def _make(user):
        from rest_framework_simplejwt.tokens import RefreshToken

        token = RefreshToken.for_user(user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
        return api_client

    return _make
