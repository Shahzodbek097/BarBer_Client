"""Kunlik eslatma zanjiri testlari: Telegram yo'li, SMS fallback, idempotentlik."""

from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.bookings.factories import AppointmentFactory
from apps.bookings.models import AppointmentStatus
from apps.notifications.models import Notification, NotificationType
from apps.telegram.models import TelegramChat
from apps.telegram.services.reminders import send_reminders_for
from apps.telegram.tasks import send_reminders_task

pytestmark = pytest.mark.django_db


def _confirmed_today():
    return AppointmentFactory(
        date=timezone.localdate(),
        status=AppointmentStatus.CONFIRMED,
    )


class TestRemindersTelegramPath:
    def test_linked_client_gets_reminder(self, fake_bot):
        appt = _confirmed_today()
        chat = TelegramChat.objects.create(user=appt.client, chat_id=999)

        sent = send_reminders_for(timezone.localdate())

        assert sent == 1
        appt.refresh_from_db()
        assert appt.reminded_at is not None
        # web xabarnoma ham yaratildi (post_save ko'prik orqali Telegram)
        note = Notification.objects.get(
            recipient=appt.client, type=NotificationType.BOOKING_REMINDER
        )
        assert "Bugun" in note.body
        assert any(
            m["chat_id"] == chat.chat_id and "eslatma" in m["text"].lower() for m in fake_bot
        )

    def test_idempotent_second_run_empty(self, fake_bot):
        _confirmed_today()
        assert send_reminders_for(timezone.localdate()) == 1
        assert send_reminders_for(timezone.localdate()) == 0
        assert Notification.objects.filter(type=NotificationType.BOOKING_REMINDER).count() == 1

    def test_only_confirmed_sent(self, fake_bot, fake_reminder_sms):
        pending = AppointmentFactory(date=timezone.localdate(), status=AppointmentStatus.PENDING)
        completed = AppointmentFactory(
            date=timezone.localdate(), status=AppointmentStatus.COMPLETED
        )
        sent = send_reminders_for(timezone.localdate())
        assert sent == 0
        assert fake_reminder_sms == []
        pending.refresh_from_db()
        completed.refresh_from_db()
        assert pending.reminded_at is None and completed.reminded_at is None

    def test_other_day_ignored(self, fake_bot):
        AppointmentFactory(
            date=timezone.localdate() + timedelta(days=1),
            status=AppointmentStatus.CONFIRMED,
        )
        assert send_reminders_for(timezone.localdate()) == 0


class TestRemindersSmsFallback:
    def test_no_chat_sms_sent(self, fake_bot, fake_reminder_sms):
        appt = _confirmed_today()

        sent = send_reminders_for(timezone.localdate())

        assert sent == 1
        assert len(fake_reminder_sms) == 1
        assert fake_reminder_sms[0]["phone"] == appt.client.phone
        assert "navbatingiz bor" in fake_reminder_sms[0]["message"]
        # chat yo'q — Telegram yuborilmadi
        assert fake_bot == []

    def test_sms_error_does_not_break_chain(self, fake_bot, fake_reminder_sms, monkeypatch):
        """SMS xatosi eslatma yozuvini (Notification + reminded_at) buzmaydi."""

        class BrokenSMS:
            name = "broken"

            def send(self, phone, message):
                raise RuntimeError("sms down")

        monkeypatch.setattr("apps.telegram.services.reminders.get_sms_client", lambda: BrokenSMS())
        appt = _confirmed_today()
        sent = send_reminders_for(timezone.localdate())
        assert sent == 1
        appt.refresh_from_db()
        assert appt.reminded_at is not None


class TestTasksAndCommand:
    def test_celery_task_eager(self, fake_bot):
        _confirmed_today()
        result = send_reminders_task()
        assert result == 1

    def test_management_command(self, fake_bot, capsys):
        _confirmed_today()
        call_command("send_reminders", "--day", timezone.localdate().isoformat())
        out = capsys.readouterr().out
        assert "1 eslatma yuborildi" in out
