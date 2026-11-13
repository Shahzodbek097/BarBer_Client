"""Lokal ishlab chiqish sozlamalari (manage.py va Docker'dagi web default)."""

from .base import *  # noqa: F401, F403
from .base import env

DEBUG = env.bool("DEBUG", default=True)

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]

# Dev'da iframe ichida sahifalarni responsive tekshirish uchun
# (prod'da DENY qoladi — clickjacking himoyasi)
X_FRAME_OPTIONS = "SAMEORIGIN"

# Dev'da email (va keyin SMS) konsolga yoziladi
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
