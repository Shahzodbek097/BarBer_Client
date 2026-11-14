"""Telegram bog'lanish API testlari (`/api/v1/telegram/link/`)."""

import pytest

from apps.accounts.factories import UserFactory
from apps.accounts.models import User
from apps.telegram.models import TelegramChat

pytestmark = pytest.mark.django_db

URL = "/api/v1/telegram/link/"


class TestTelegramLinkApi:
    def test_unauthenticated_401(self, api_client):
        assert api_client.get(URL).status_code == 401

    def test_status_unlinked(self, api_client, make_auth_client):
        user = UserFactory()
        response = make_auth_client(user).get(URL)
        assert response.status_code == 200
        data = response.json()
        assert data["linked"] is False
        assert data["bot_username"]

    def test_post_creates_code(self, api_client, make_auth_client):
        user = UserFactory()
        response = make_auth_client(user).post(URL)
        assert response.status_code == 201
        data = response.json()
        assert data["code"].isdigit() and len(data["code"]) == 6
        assert data["expires_at"]

    def test_status_linked(self, api_client, make_auth_client):
        user = UserFactory()
        TelegramChat.objects.create(user=user, chat_id=123, username="ali")
        data = make_auth_client(user).get(URL).json()
        assert data["linked"] is True
        assert data["chat_id"] == 123
        assert data["username"] == "ali"

    def test_client_role_allowed(self, api_client, make_auth_client):
        user = UserFactory(role=User.Role.CLIENT)
        assert make_auth_client(user).post(URL).status_code == 201

    def test_barber_role_allowed(self, api_client, make_auth_client):
        user = UserFactory(role=User.Role.BARBER)
        assert make_auth_client(user).post(URL).status_code == 201
