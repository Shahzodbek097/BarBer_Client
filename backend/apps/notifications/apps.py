from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"

    def ready(self) -> None:
        # Navbat hodisalaridan xabarnoma signal'lari (import yo'nalishi
        # qoidasi tufayli signal orqali bog'lanadi)
        from apps.notifications import signals  # noqa: F401
