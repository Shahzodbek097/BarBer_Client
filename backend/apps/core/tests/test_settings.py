"""Bosqich 1: sozlamalar va konfiguratsiya smoke testlari."""

from django.conf import settings

EXPECTED_LOCAL_APPS = [
    "core",
    "accounts",
    "salons",
    "barbers",
    "services",
    "schedule",
    "bookings",
    "notifications",
    "reviews",
    "analytics",
]


def test_timezone_is_tashkent():
    assert settings.TIME_ZONE == "Asia/Tashkent"


def test_all_local_apps_registered():
    for label in EXPECTED_LOCAL_APPS:
        assert f"apps.{label}" in settings.INSTALLED_APPS


def test_test_settings_is_safe():
    # Test muhiti hech qachon DEBUG bilan ishlamasligi kerak
    assert settings.DEBUG is False
    assert settings.CELERY_TASK_ALWAYS_EAGER is True
