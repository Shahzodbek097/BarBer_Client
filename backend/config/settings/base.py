"""
BarBer_Client — umumiy sozlamalar (barcha muhitlar uchun asos).

Muhitga xos qiymatlar .env orqali kelinadi (12-Factor uslubi).
Muhitga xos sozlamalar: settings/dev.py, settings/test.py, settings/prod.py
"""

from datetime import timedelta
from pathlib import Path

import environ

# backend/ papkasi
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, "insecure-dev-only-key"),
    ALLOWED_HOSTS=(list, []),
    DATABASE_URL=(str, "postgres://barber:barber@localhost:5432/barber_client"),
    REDIS_URL=(str, "redis://localhost:6379/0"),
    REDIS_BROKER_URL=(str, "redis://localhost:6379/1"),
    TIME_ZONE=(str, "Asia/Tashkent"),
)

# Repo ildizidagi .env fayl (backend/../.env). Mavjud os.environ o'zgaruvchilari
# ustuvorlik oladi (CI va Docker'da fayl yo'q bo'lsa ham ishlaydi).
environ.Env.read_env(BASE_DIR.parent / ".env")

# --- Xavfsizlik ---
SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# --- Django ilovalari ---
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    # JWT blacklist (logout/rotation uchun token bazasi)
    "rest_framework_simplejwt.token_blacklist",
    # WebSocket (bosqich 5)
    "channels",
    # OpenAPI sxema generatori (Swagger)
    "drf_spectacular",
]

LOCAL_APPS = [
    "apps.core",
    "apps.accounts",
    "apps.salons",
    "apps.barbers",
    "apps.services",
    "apps.schedule",
    "apps.bookings",
    "apps.notifications",
    "apps.reviews",
    "apps.analytics",
]

# Daphne runserver'ni ASGI/WS-ga o'tkazadi — INSTALLED_APPS boshida turishi shart
INSTALLED_APPS = ["daphne", *DJANGO_APPS, *THIRD_PARTY_APPS, *LOCAL_APPS]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

ASGI_APPLICATION = "config.asgi.application"

# WebSocket channel layer: dev/prod — Redis (6379/2, broker 0/1 dan alohida)
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [env("REDIS_CHANNEL_URL", default="redis://localhost:6379/2")]},
    }
}

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR.parent / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# --- Ma'lumotlar bazasi ---
DATABASES = {
    "default": env.db("DATABASE_URL"),
}
DATABASES["default"]["CONN_MAX_AGE"] = 60

# --- Kesh / broker ---
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL"),
    }
}

# --- Celery (task'lar 4-bosqichdan boshlanadi, Beat 7-bosqichda) ---
CELERY_BROKER_URL = env("REDIS_BROKER_URL")
CELERY_RESULT_BACKEND = env("REDIS_BROKER_URL")
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_ACKS_LATE = True

# --- Internatsionalizatsiya ---
LANGUAGE_CODE = "uz"
TIME_ZONE = env("TIME_ZONE")
USE_I18N = True
USE_TZ = True

# --- Statik va media ---
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Autentifikatsiya ---
# Custom user: telefon = login identifikator (bosqich 2)
AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- DRF (bosqich 3: JWT auth, throttle) ---
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
        "apps.accounts.permissions.IsNotBlocked",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "register": "5/min",
        "otp": "5/min",  # login/dam olish: plan — login 5/min
        "otp_verify": "10/min",
    },
    # OpenAPI sxema generatori (Swagger)
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "BarBer_Client API",
    "DESCRIPTION": "Sartaroshxona va sartarosh onlayn navbat platformasi (v1).",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": "/api/v1",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# OTP xavfsizlik sozlamalari (TZ 6.1: Eskiz, 3 urinish limit)
OTP_CONFIG = {
    "LIFETIME_SECONDS": 300,  # 5 daqiqa
    "MAX_ATTEMPTS": 3,
    "RESEND_COOLDOWN_SECONDS": 60,
    "HOURLY_LIMIT": 5,  # bir telefon: soatiga 5 kod
    "LENGTH": 5,
}

# --- SMS / Telegram (3 va 7-bosqichlar ishlatadi) ---
SMS_PROVIDER = env("SMS_PROVIDER", default="console")  # console | eskiz
SMS_ESKIZ_EMAIL = env("SMS_ESKIZ_EMAIL", default="")
SMS_ESKIZ_PASSWORD = env("SMS_ESKIZ_PASSWORD", default="")
TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN", default="")

# --- Logging ---
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
    },
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
}
