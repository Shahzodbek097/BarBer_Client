"""Audit jurnali yozuvi (barcha app'lar ishlatadi — core eng past qatlam)."""

from apps.core.models import AuditLog


def log_action(
    actor, action: str, model_name: str = "", object_id: str = "", payload: dict | None = None
) -> None:
    """Muhim harakatni jurnalga yozadi. Hech qachon exception oshirmaydi."""
    try:
        AuditLog.objects.create(
            actor=actor,
            action=action,
            model_name=model_name,
            object_id=str(object_id) if object_id else "",
            payload=payload or {},
        )
    except Exception:  # noqa: BLE001 — audit hech qachon asosiy oqimni buzmasligi kerak
        pass
