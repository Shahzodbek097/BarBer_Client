"""Navbat factory'lari.

Eslatma: factory_boy deklaratsiyalar alifbo tartibida baholaydi —
`barber` (b) `service` (s) dan oldin yaratiladi, shuning uchun
`SelfAttribute("..barber")` xizmatga navbat sartaroshini beradi.
"""

from datetime import time, timedelta
from decimal import Decimal

import factory
from django.utils import timezone

from apps.accounts.factories import UserFactory
from apps.barbers.factories import BarberProfileFactory
from apps.bookings.models import Appointment, AppointmentHistory, AppointmentStatus
from apps.services.factories import ServiceFactory


class AppointmentFactory(factory.django.DjangoModelFactory):
    """Mijoz navbati.

    service.barber = navbat sartaroshi (moslik sharti),
    salon = sartarosh saloni, price = xizmat narxi snapshot.
    Default vaqt: ertaga 10:00-10:30 (ServiceFactory.duration_min=30 ga mos).
    """

    class Meta:
        model = Appointment

    client = factory.SubFactory(UserFactory)
    barber = factory.SubFactory(BarberProfileFactory)
    service = factory.SubFactory(
        ServiceFactory,
        barber=factory.SelfAttribute("..barber"),
    )
    salon = factory.SelfAttribute("barber.salon")
    date = factory.LazyFunction(lambda: timezone.localdate() + timedelta(days=1))
    start_time = time(10, 0)
    end_time = time(10, 30)
    price = Decimal("50000.00")


class AppointmentHistoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AppointmentHistory

    appointment = factory.SubFactory(AppointmentFactory)
    new_status = AppointmentStatus.PENDING
