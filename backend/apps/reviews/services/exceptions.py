"""Sharh domen xatolari (bosqich 5)."""

from rest_framework.exceptions import APIException


class ReviewError(APIException):
    status_code = 400


class ReviewValidationError(ReviewError):
    status_code = 400
    default_detail = "Sharh qo'shib bo'lmadi."
    default_code = "review_invalid"


class ReviewNotOwner(ReviewError):
    status_code = 403
    default_detail = "Bu navbat sizga tegishli emas."
    default_code = "not_owner"


__all__ = ["ReviewError", "ReviewValidationError", "ReviewNotOwner"]
