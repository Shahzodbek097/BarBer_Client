"""Production sozlamalari (9-bosqichda Docker bilan qo'llanadi).

Ishga tushirish: DJANGO_SETTINGS_MODULE=config.settings.prod
"""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401, F403
from .base import BASE_DIR, SECRET_KEY, env

DEBUG = False

if SECRET_KEY == "insecure-dev-only-key":
    raise ImproperlyConfigured(
        "Production'da SECRET_KEY .env faylida mustaqil qiymat bilan o'rnatilishi shart."
    )

ALLOWED_HOSTS = env("ALLOWED_HOSTS")
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("Production'da ALLOWED_HOSTS o'rnatilishi shart.")

# --- Transport xavfsizligi ---
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31_536_000  # 1 yil
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# --- Logging: konsol + aylanadigan fayl ---
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} [{name}] {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "verbose",
            "filename": LOGS_DIR / "barber.log",
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
        },
    },
    "root": {"handlers": ["console", "file"], "level": "INFO"},
}
