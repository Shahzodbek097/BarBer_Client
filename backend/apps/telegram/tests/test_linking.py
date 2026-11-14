"""Chat bog'lash oqimi testlari (kabinet kodi → bot /start KOD)."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.factories import UserFactory
from apps.telegram.models import LinkCode, TelegramChat
from apps.telegram.services.linking import TelegramLinkError, create_link_code, link_chat

pytestmark = pytest.mark.django_db


class TestCreateLinkCode:
    def test_creates_six_digit_code(self):
        user = UserFactory()
        link = create_link_code(user)
        assert link.code.isdigit() and len(link.code) == 6
        assert link.used_at is None
        assert link.expires_at > timezone.now()

    def test_invalidates_previous_codes(self):
        user = UserFactory()
        old = create_link_code(user)
        new = create_link_code(user)
        old.refresh_from_db()
        assert old.used_at is not None  # bekor qilindi
        assert new.is_usable


class TestLinkChat:
    def test_success(self):
        user = UserFactory(full_name="Ali Mijoz")
        link = create_link_code(user)
        linked = link_chat(link.code, 555111, username="ali_uz")
        assert linked.pk == user.pk
        chat = TelegramChat.objects.get(user=user)
        assert chat.chat_id == 555111
        assert chat.username == "ali_uz"
        assert chat.is_active
        link.refresh_from_db()
        assert link.used_at is not None

    def test_unknown_code(self):
        with pytest.raises(TelegramLinkError, match="topilmadi"):
            link_chat("000000", 1)

    def test_used_code_rejected(self):
        user = UserFactory()
        link = create_link_code(user)
        link_chat(link.code, 1)
        with pytest.raises(TelegramLinkError, match="ishlatilgan"):
            link_chat(link.code, 2)

    def test_expired_code_rejected(self):
        user = UserFactory()
        link = create_link_code(user)
        LinkCode.objects.filter(pk=link.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        with pytest.raises(TelegramLinkError, match="tugagan"):
            link_chat(link.code, 2)

    def test_relink_updates_same_chat_row(self):
        user = UserFactory()
        first = link_chat(create_link_code(user).code, 111, "a")
        second = link_chat(create_link_code(user).code, 222, "b")
        assert first.pk == second.pk
        assert TelegramChat.objects.filter(user=user).count() == 1
        chat = TelegramChat.objects.get(user=user)
        assert (chat.chat_id, chat.username) == (222, "b")
