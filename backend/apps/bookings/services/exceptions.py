"""Booking domen xatolari.

APIException'dan meros olgani uchun DRF handler JSON xatoga aylantiradi:
- BookingValidationError -> 400 (noto'g'ri so'rov)
- AppointmentNotOwner    -> 403 (chet navbatga amal)
- SlotUnavailable        -> 409 (band yoki mavjud emas)
- InvalidTransition      -> 409 (holat mashinasi qoidabuziligi)
"""

from rest_framework.exceptions import APIException


class BookingError(APIException):
    status_code = 400


class BookingValidationError(BookingError):
    status_code = 400
    default_detail = "So'rov noto'g'ri."
    default_code = "booking_invalid"


class AppointmentNotOwner(BookingError):
    status_code = 403
    default_detail = "Bu navbat sizga tegishli emas."
    default_code = "not_owner"


class SlotUnavailable(BookingError):
    status_code = 409
    default_detail = "Bu vaqt allaqachon band yoki mavjud emas."
    default_code = "slot_unavailable"


class InvalidTransition(BookingError):
    status_code = 409
    default_detail = "Bu holat o'tishi mumkin emas."
    default_code = "invalid_transition"


__all__ = [  # noqa: RUF022
    "BookingError",
    "BookingValidationError",
    "AppointmentNotOwner",
    "SlotUnavailable",
    "InvalidTransition",
]
