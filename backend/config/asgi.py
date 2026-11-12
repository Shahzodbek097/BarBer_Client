"""ASGI konfiguratsiyasi.

- HTTP: oddiy Django ASGI ilovasi (DRF)
- WebSocket: /ws/client/{user_id}/ va /ws/barber/{user_id}/ — xabarnoma
  push kanallari (bosqich 5). Ikkalasi ham bir xil `NotifyConsumer`ga
  boradi: {user_id} — user jadvalining ID'si (sartarosh uchun ham
  BarberProfile.id emas, balki user.id ishlatiladi).
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

django_asgi_app = get_asgi_application()

from channels.auth import AuthMiddlewareStack  # noqa: E402
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import AllowedHostsOriginValidator  # noqa: E402
from django.urls import path  # noqa: E402

from apps.notifications.consumers import NotifyConsumer  # noqa: E402

websocket_urlpatterns = [
    path("ws/client/<int:user_id>/", NotifyConsumer.as_asgi()),
    path("ws/barber/<int:user_id>/", NotifyConsumer.as_asgi()),
]

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
        ),
    }
)
