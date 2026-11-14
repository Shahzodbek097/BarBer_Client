"""Webhook testlari: secret himoyasi va buyruqlar."""

import pytest

from apps.accounts.factories import UserFactory
from apps.telegram.models import TelegramChat
from apps.telegram.services.linking import create_link_code

pytestmark = pytest.mark.django_db

WEBHOOK = "/telegram/webhook/devsecret/"


@pytest.fixture(autouse=True)
def _webhook_secret(settings):
    settings.TELEGRAM_WEBHOOK_SECRET = "devsecret"


def _update(text: str, chat_id: int = 42, username: str = "ali_uz") -> dict:
    return {
        "update_id": 1,
        "message": {
            "text": text,
            "chat": {"id": chat_id, "username": username, "type": "private"},
        },
    }


class TestWebhookSecret:
    def test_wrong_secret_403(self, client):
        response = client.post(
            "/telegram/webhook/other/", _update("/start 123456"), content_type="application/json"
        )
        assert response.status_code == 403

    def test_empty_setting_403(self, client, settings):
        settings.TELEGRAM_WEBHOOK_SECRET = ""
        response = client.post(WEBHOOK, _update("/start 123456"), content_type="application/json")
        assert response.status_code == 403

    def test_get_not_allowed(self, client):
        assert client.get(WEBHOOK).status_code == 405


class TestWebhookCommands:
    def test_start_with_code_links_chat(self, client, fake_bot):
        user = UserFactory(full_name="Ali Mijoz")
        code = create_link_code(user).code

        response = client.post(WEBHOOK, _update(f"/start {code}"), content_type="application/json")

        assert response.status_code == 200
        assert response.json() == {"ok": True}
        chat = TelegramChat.objects.get(user=user)
        assert chat.chat_id == 42
        # javob ham bot orqali yuborildi
        assert any(
            str(chat.chat_id) == str(m["chat_id"]) and "Ali Mijoz" in m["text"] for m in fake_bot
        )

    def test_start_without_code_hints(self, client, fake_bot):
        response = client.post(WEBHOOK, _update("/start"), content_type="application/json")
        assert response.status_code == 200
        assert any("Kod bilan" in m["text"] for m in fake_bot)

    def test_unknown_text_helps(self, client, fake_bot):
        response = client.post(WEBHOOK, _update("salom"), content_type="application/json")
        assert response.status_code == 200
        assert any("xush kelibsiz" in m["text"] for m in fake_bot)

    def test_invalid_code_error_reply(self, client, fake_bot):
        response = client.post(WEBHOOK, _update("/start 999999"), content_type="application/json")
        assert response.status_code == 200
        assert any("topilmadi" in m["text"] for m in fake_bot)
        assert TelegramChat.objects.count() == 0

    def test_malformed_body_ok(self, client):
        response = client.post(WEBHOOK, b"not-json", content_type="application/json")
        assert response.status_code == 200
        assert response.json() == {"ok": True}

    def test_non_text_update_ignored(self, client, fake_bot):
        response = client.post(
            WEBHOOK, {"message": {"chat": {"id": 1}}}, content_type="application/json"
        )
        assert response.status_code == 200
        assert fake_bot == []
