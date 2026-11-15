"""Lokal ishlab chiqish sozlamalari (manage.py va Docker'dagi web default)."""

from .base import *  # noqa: F401, F403
from .base import MIDDLEWARE, env

DEBUG = env.bool("DEBUG", default=True)

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]

# --- Statik fayllar: whitenoise (finders rejimi) ---
# Dev'da `runserver` emas, gunicorn ishlaydi (bosqich 8: yuk p95 242 ms) —
# gunicorn finders orqali statik bermaydi (runserver'dagidek). Whitenoise
# USE_FINDERS bilan app static'larini collectstatic'siz topadi;
# AUTOREFRESH — fayl o'zgarsa darhol ko'rinadi (faqat DEBUG'da).
MIDDLEWARE = [
    *MIDDLEWARE[:1],
    "whitenoise.middleware.WhiteNoiseMiddleware",  # SecurityMiddleware'dan keyin
    *MIDDLEWARE[1:],
]
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = True

# Dev'da iframe ichida sahifalarni responsive tekshirish uchun
# (prod'da DENY qoladi — clickjacking himoyasi)
X_FRAME_OPTIONS = "SAMEORIGIN"

# Dev'da email (va keyin SMS) konsolga yoziladi
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
