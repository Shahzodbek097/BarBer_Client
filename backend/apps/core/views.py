"""Umumiy infrastrukturaviy view'lar."""

import time

from django.http import JsonResponse


def health(request):
    """Servis sog'lomligi (bosqich 1).

    DB/Redis chuqur tekshiruvi 9-bosqichda (deploy monitoring) kengaytiriladi.
    """
    return JsonResponse(
        {
            "status": "ok",
            "service": "BarBer_Client",
            "timestamp": int(time.time()),
        }
    )
