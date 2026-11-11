"""Test muhit sozlamalari: izolyatsiyalangan va tez."""

from .base import *  # noqa: F401, F403
from .base import env

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
