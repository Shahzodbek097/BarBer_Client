"""Bosqich 2: Notification model testlari."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.notifications.factories import NotificationFactory
from apps.notifications.models import Notification, NotificationType

pytestmark = pytest.mark.django_db


class TestNotification:
    def test_defaults_unread(self):
        notification = NotificationFactory()

        assert notification.is_read is False
        assert notification.link == ""
        assert notification.body == ""

    def test_str_shows_title(self):
        notification = NotificationFactory(title="Navbat tasdiqlandi")

        assert "Navbat tasdiqlandi" in str(notification)

    def test_booking_types_exist(self):
        expected = {
            "booking_new",
            "booking_confirmed",
            "booking_rejected",
            "booking_proposed",
            "booking_rescheduled",
            "booking_cancelled",
            "booking_completed",
            "booking_reminder",
            "system",
        }

        assert set(NotificationType.values) == expected

    def test_ordering_newest_first(self):
        old = NotificationFactory()
        new = NotificationFactory(recipient=old.recipient)
        # created_at auto_now_add — farqni qo'lda beramiz
        Notification.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(hours=1)
        )

        assert Notification.objects.first() == new
        assert list(old.recipient.notifications.all()) == [new, old]
