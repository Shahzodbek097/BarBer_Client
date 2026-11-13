"""Veb template kontekstlari (bosqich 6)."""

from django.conf import settings


def static_version(request):
    """Statik fayllarga versiya query parametri — keshni yangilash uchun."""
    return {"STATIC_VERSION": settings.STATIC_VERSION}
