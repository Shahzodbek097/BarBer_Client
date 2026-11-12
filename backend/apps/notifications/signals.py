"""Navbat hodisalaridan xabarnoma yaratish (signal orqali).

Signal tanlovi: `bookings` → `notifications` import qilib bo'lmaydi
(importlar faqat yuqoriga), shuning uchun bog'lanish DB signal'lari
orqali amalga oshiriladi — notifications yuqorida turgani uchun
bookings modellarini import qilish qonuniy.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.bookings.models import Appointment, AppointmentHistory, AppointmentStatus
from apps.notifications.models import NotificationType
from apps.notifications.services.emitter import notify

# Terminal holatlar uchun xabar turlari
STATUS_TO_TYPE = {
    AppointmentStatus.CONFIRMED: NotificationType.BOOKING_CONFIRMED,
    AppointmentStatus.REJECTED: NotificationType.BOOKING_REJECTED,
    AppointmentStatus.CANCELLED: NotificationType.BOOKING_CANCELLED,
    AppointmentStatus.COMPLETED: NotificationType.BOOKING_COMPLETED,
    AppointmentStatus.NO_SHOW: NotificationType.SYSTEM,
}

STATUS_TITLES = {
    AppointmentStatus.CONFIRMED: "Navbat tasdiqlandi",
    AppointmentStatus.REJECTED: "Navbat rad etildi",
    AppointmentStatus.CANCELLED: "Navbat bekor qilindi",
    AppointmentStatus.COMPLETED: "Xizmat bajarildi",
    AppointmentStatus.NO_SHOW: "Mijoz kelmadi",
}


def _slot_text(appointment: Appointment) -> str:
    return f"{appointment.date:%d.%m} {appointment.start_time:%H:%M}"


@receiver(post_save, sender=Appointment)
def on_appointment_created(sender, instance, created, **kwargs) -> None:
    """Yangi navbat → sartaroshga push (WS yangi so'rov kanali)."""
    if not created:
        return
    notify(
        recipient=instance.barber.user,
        ntype=NotificationType.BOOKING_NEW,
        title="Yangi navbat so'rovi",
        body=f"{instance.client.full_name} {_slot_text(instance)} ga navbat oldi.",
        link=f"/barber/bookings/{instance.pk}",
    )


@receiver(post_save, sender=AppointmentHistory)
def on_history_created(sender, instance, created, **kwargs) -> None:
    """Har holat o'tishi → qarama-qarshi tomonga xabarnoma."""
    if not created or instance.old_status is None:
        return  # yaratilish yozuvi (create_appointment yozadi)

    appointment = instance.appointment
    changed_by_client = instance.changed_by_id == appointment.client_id

    if instance.old_status == instance.new_status == AppointmentStatus.PENDING:
        # vaqt ko'chishi: mijoz reschedule yoki sartarosh propose
        if changed_by_client:
            notify(
                recipient=appointment.barber.user,
                ntype=NotificationType.BOOKING_RESCHEDULED,
                title="Navbat vaqti o'zgartirildi",
                body=f"Mijoz navbatni {_slot_text(appointment)} ga ko'chirdi.",
                link=f"/barber/bookings/{appointment.pk}",
            )
        else:
            notify(
                recipient=appointment.client,
                ntype=NotificationType.BOOKING_PROPOSED,
                title="Boshqa vaqt taklif qilindi",
                body=(
                    f"Sartarosh navbatni {_slot_text(appointment)} ga taklif qildi. "
                    f"{appointment.barber_reply}"
                ),
                link=f"/c/bookings/{appointment.pk}",
            )
        return

    ntype = STATUS_TO_TYPE.get(instance.new_status, NotificationType.SYSTEM)
    title = STATUS_TITLES.get(instance.new_status, "Navbat holati o'zgardi")
    recipient = appointment.barber.user if changed_by_client else appointment.client
    notify(
        recipient=recipient,
        ntype=ntype,
        title=title,
        body=f"Navbat ({_slot_text(appointment)}) holati: {title.lower()}.",
        link=f"/c/bookings/{appointment.pk}"
        if not changed_by_client
        else f"/barber/bookings/{appointment.pk}",
    )
