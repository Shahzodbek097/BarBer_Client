"""Xabarnoma yaratilganda Telegram'ga ham yuborish.

Import yo'nalishi qonuniy: telegram (pastda) → notifications (yuqorida).
`notifications` tomondan `telegram`'ni import qilmasligi kerak — shuning
uchun bog'lanish Django `post_save` signal orqali (`TelegramConfig.ready`).
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.notifications.models import Notification, NotificationType
from apps.telegram.services.notifier import send_to_user


@receiver(post_save, sender=Notification)
def on_notification_created(sender, instance: Notification, created: bool, **kwargs) -> None:
    """Navbat zanjiri (navbat → tasdiq → eslatma) Telegram'ga ko'chiriladi."""
    if not created or instance.type == NotificationType.SYSTEM:
        return
    send_to_user(instance.recipient, instance.title, instance.body)
