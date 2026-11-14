"""Notification → Telegram ko'prik testlari (post_save)."""

import pytest

from apps.accounts.factories import UserFactory
from apps.bookings.factories import AppointmentFactory
from apps.bookings.models import AppointmentStatus
from apps.bookings.services.state_machine import transition
from apps.notifications.models import Notification, NotificationType
from apps.telegram.models import TelegramChat

pytestmark = pytest.mark.django_db


def _link(user, chat_id=777):
    return TelegramChat.objects.create(user=user, chat_id=chat_id)


class TestNotifierBridge:
    def test_linked_chat_receives_telegram(self, fake_bot):
        user = UserFactory()
        _link(user, 777)
        Notification.objects.create(
            recipient=user, type=NotificationType.BOOKING_CONFIRMED, title="Navbat tasdiqlandi"
        )
        assert len(fake_bot) == 1
        assert fake_bot[0]["chat_id"] == 777
        assert "Navbat tasdiqlandi" in fake_bot[0]["text"]

    def test_unlinked_user_no_send(self, fake_bot):
        user = UserFactory()
        Notification.objects.create(
            recipient=user, type=NotificationType.BOOKING_CONFIRMED, title="x"
        )
        assert fake_bot == []

    def test_system_type_skipped(self, fake_bot):
        user = UserFactory()
        _link(user)
        Notification.objects.create(recipient=user, type=NotificationType.SYSTEM, title="x")
        assert fake_bot == []

    def test_bot_error_does_not_break_flow(self, monkeypatch):
        """Bot xatosi Notification yaratishni buzmasligi kerak."""

        class BrokenBot:
            name = "broken"

            def send_message(self, chat_id, text):
                raise RuntimeError("telegram down")

        monkeypatch.setattr("apps.telegram.services.notifier.get_bot", lambda: BrokenBot())
        user = UserFactory()
        _link(user)
        Notification.objects.create(
            recipient=user, type=NotificationType.BOOKING_COMPLETED, title="ok"
        )
        assert Notification.objects.count() == 1


class TestChainIntegration:
    """Zanjir: navbat yaratildi → tasdiqlandi → Telegram xabarlari ketadi."""

    def test_booking_events_send_telegram(self, fake_bot):
        appt = AppointmentFactory()
        # Yaratilish xabari sartaroshga ketadi, lekin chat yo'q — yuborilmaydi
        assert fake_bot == []

        # Sartarosh tasdiqlaydi → xabar MIJOZga ketadi; mijoz chatini bog'laymiz
        chat = _link(appt.client, 888)
        transition(appt, AppointmentStatus.CONFIRMED, changed_by=appt.barber.user)
        assert any(
            m["chat_id"] == chat.chat_id and "tasdiqlandi" in m["text"].lower() for m in fake_bot
        )
