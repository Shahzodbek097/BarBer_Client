"""BarBer_Client URL konfiguratsiyasi.

Bosqich 5: REST router (`config.api_router`), Swagger sxemasi va WS.
"""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.telegram.webhook import telegram_webhook

urlpatterns = [
    path("admin/", admin.site.urls),
    # OpenAPI (Swagger gate)
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("api/v1/auth/", include("apps.accounts.api.urls")),
    path("api/v1/", include("config.api_router")),
    # Telegram webhook (bosqich 7) — bot API'ga ochiq, secret bilan himoyalangan
    path("telegram/webhook/<str:secret>/", telegram_webhook),
    path("", include("apps.web.urls")),
    path("", include("apps.core.urls")),
]

# Prod (DEBUG=False): whitenoise faqat STATIC xizmatlaydi — MEDIA (salon
# suratlari) uchun Django'ning oddiy serve fallback'i (kichik hajm uchun
# yetarli; yuk ortsa nginx/caddy old panelga o'tkaziladi).
if not settings.DEBUG:
    from django.views.static import serve as media_serve

    urlpatterns += [
        path(
            "media/<path:path>",
            media_serve,
            {"document_root": settings.MEDIA_ROOT},
        ),
    ]
