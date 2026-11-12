"""Global statistika (super admin panel uchun).

`bookings` qatlamida joylashgan — barcha kerakli app'lar (accounts,
salons, barbers) undan PASTda, shuning uchun import yo'nalishi
qoidasi buzilmaydi. Og'ir tahlillar (kunlik hisobotlar) bosqich 7.
"""

from django.utils import timezone

from apps.accounts.models import User
from apps.barbers.models import BarberProfile
from apps.bookings.models import Appointment, AppointmentStatus
from apps.salons.models import Salon, SalonStatus


def global_stats() -> dict:
    """Umumiy hisoblar (bir nechta count so'rovi)."""
    today = timezone.localdate()

    users_by_role = {role: User.objects.filter(role=role).count() for role, _ in User.Role.choices}
    salons_by_status = {
        status: Salon.objects.filter(status=status).count() for status, _ in SalonStatus.choices
    }
    appointments_by_status = {
        status: Appointment.objects.filter(status=status).count()
        for status, _ in AppointmentStatus.choices
    }

    return {
        "users": {
            "total": User.objects.count(),
            "by_role": users_by_role,
        },
        "barbers_total": BarberProfile.objects.count(),
        "salons": {
            "total": Salon.objects.count(),
            "by_status": salons_by_status,
        },
        "appointments": {
            "total": Appointment.objects.count(),
            "today": Appointment.objects.filter(date=today).count(),
            "by_status": appointments_by_status,
        },
    }
