"""Xabarnoma factory."""

import factory

from apps.accounts.factories import UserFactory
from apps.notifications.models import Notification, NotificationType


class NotificationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Notification

    recipient = factory.SubFactory(UserFactory)
    type = NotificationType.BOOKING_NEW
    title = factory.Sequence(lambda n: f"Xabarnoma {n + 1}")
