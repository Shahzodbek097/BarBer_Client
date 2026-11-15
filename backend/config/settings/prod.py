"""Production sozlamalari (9-bosqichda Docker bilan qo'llanadi).

Ishga tushirish: DJANGO_SETTINGS_MODULE=config.settings.prod
"""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401, F403
from .base import BASE_DIR, MIDDLEWARE, SECRET_KEY, env

DEBUG = False

if SECRET_KEY == "insecure-dev-only-key":
    raise ImproperlyConfigured(
        "Production'da SECRET_KEY .env faylida mustaqil qiymat bilan o'rnatilishi shart."
    )

ALLOWED_HOSTS = env("ALLOWED_HOSTS")
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("Production'da ALLOWED_HOSTS o'rnatilishi shart.")

# --- Transport xavfsizligi ---
# TLS reverse proxy ortida ishlaydi (proxy X-Forwarded-Proto yuboradi)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# Lokal HTTP drill (TLS'siz konteyner) uchun o'chiriladi; domain'da True
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SECURE_HSTS_SECONDS = 31_536_000  # 1 yil
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# --- Statik fayllar: whitenoise (collectstatic → gzip) ---
MIDDLEWARE = [
    *MIDDLEWARE[:1],
    "whitenoise.middleware.WhiteNoiseMiddleware",  # SecurityMiddleware'dan keyin
    *MIDDLEWARE[1:],
]
STORAGES = {
    # default — FileField (salon suratlari); uni yo'qotib qo'ymaslik shart
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        # Manifest emas — cache-busting ?v=<STATIC_VERSION> bilan (web context)
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

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
