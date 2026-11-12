"""Test muhit sozlamalari: izolyatsiyalangan va tez."""

from .base import *  # noqa: F401, F403
from .base import REST_FRAMEWORK, env

DEBUG = False

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]

# Test bazasi: DATABASE_URL berilmasa, alohida test DB ishlatiladi
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://barber:barber@localhost:5432/barber_client_test",
    )
}

# Kesh: in-memory (Redis talab qilinmaydi)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Celery task'lari testda sinxron ishlaydi
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Parol hashing: tezroq
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Throttle: testlarda limitlar juda yumshoq (ayrim testlar override qilib toraytiradi)
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {
    **REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"],
    "register": "1000/min",
    "otp": "1000/min",
    "otp_verify": "1000/min",
}

# WebSocket: testlarda Redis kerak emas — in-memory channel layer
CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
