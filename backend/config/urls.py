"""BarBer_Client URL konfiguratsiyasi.

Bosqich 3: auth endpointlar; bosqich 5-da `config/api_router.py` shu yerda
kengaytiriladi.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("apps.accounts.api.urls")),
    path("", include("apps.core.urls")),
]
