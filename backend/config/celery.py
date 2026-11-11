"""Celery ilova konfiguratsiyasi.

Task'lar 4-bosqichdan (biznes mantiq), Beat jadvali 7-bosqichdan qo'shiladi.
Lokal run: docker compose'dagi `celery` xizmati yoki
`celery -A config worker -l info`
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("barber_client")

# Sozlamalarni Django settings'dan o'qiydi (CELERY_ prefiksi bilan)
app.config_from_object("django.conf:settings", namespace="CELERY")

# Har app'ning tasks.py faylini avtomatik topadi
app.autodiscover_tasks()
