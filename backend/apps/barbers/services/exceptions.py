"""Sartarosh kabineti xatolari (bosqich 5 API uchun)."""

from rest_framework.exceptions import APIException


class CabinetError(APIException):
    status_code = 400


class CabinetValidationError(CabinetError):
    status_code = 400
    default_detail = "So'rov noto'g'ri."
    default_code = "cabinet_invalid"


__all__ = ["CabinetError", "CabinetValidationError"]
