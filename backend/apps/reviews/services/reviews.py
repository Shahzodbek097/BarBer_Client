"""Sharh biznes mantiq (bosqich 5).

Qoidalar (bosqich 2 model izohi):
- faqat COMPLETED navbatga yoziladi
- har navbat = 1 sharh (OneToOne)
- yaratilganda sartarosh rating'i qayta hisoblanadi
"""

from django.db.models import Avg, Count

from apps.bookings.models import Appointment, AppointmentStatus
from apps.core.services.audit import log_action
from apps.reviews.models import Review
from apps.reviews.services.exceptions import ReviewNotOwner, ReviewValidationError


def create_review(client, *, appointment_id: int, rating: int, comment: str = "") -> Review:
    """Sharh yozadi va sartarosh rating'ini yangilaydi."""
    appointment = Appointment.objects.select_related("barber").filter(pk=appointment_id).first()
    if appointment is None:
        raise ReviewValidationError("Navbat topilmadi.")
    if appointment.client_id != client.id:
        raise ReviewNotOwner()
    if appointment.status != AppointmentStatus.COMPLETED:
        raise ReviewValidationError("Sharh faqat bajarilgan navbat uchun yoziladi.")
    if Review.objects.filter(appointment=appointment).exists():
        raise ReviewValidationError("Bu navbat uchun sharh allaqachon yozilgan.")

    review = Review.objects.create(
        appointment=appointment,
        client=client,
        barber=appointment.barber,
        rating=rating,
        comment=comment,
    )
    _recompute_barber_rating(appointment.barber_id)

    log_action(
        actor=client,
        action="review_created",
        model_name="reviews.Review",
        object_id=review.pk,
        payload={"appointment_id": appointment_id, "rating": rating},
    )
    return review


def _recompute_barber_rating(barber_id: int) -> None:
    """Sartarosh rating_avg/rating_count ni ko'rinadigan sharhlar bo'yicha."""
    from apps.barbers.models import BarberProfile

    stats = Review.objects.filter(barber_id=barber_id, is_visible=True).aggregate(
        avg=Avg("rating"), total=Count("id")
    )
    BarberProfile.objects.filter(pk=barber_id).update(
        rating_avg=round(stats["avg"] or 0, 2), rating_count=stats["total"] or 0
    )


def barber_reviews(barber_id: int):
    """Sartaroshning ochiq sharhlari (katalog ko'radi)."""
    return Review.objects.filter(barber_id=barber_id, is_visible=True).select_related(
        "client", "appointment__service"
    )
