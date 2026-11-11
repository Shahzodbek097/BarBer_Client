"""BarBer_Client URL konfiguratsiyasi.

Bosqich 5-da `config/api_router.py` shu yerda ulanadi.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.core.urls")),
]
