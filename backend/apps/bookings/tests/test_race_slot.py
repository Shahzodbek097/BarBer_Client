"""Bosqich 4: race-test — bir slotga parallel bandlovlar.

Gate sharti: 10 thread bir vaqtda bir slotga navbat olsa -> faqat 1
g'alaba, 9 tasi SlotUnavailable (bazaviy himoya:
`appointment_active_slot_unique` partial unique index).

Ishga real Postgres kerak — pytest-django `django_db(transaction=True)`
 markeri testning o'z transaksion o'ramini olib tashlaydi va har thread
o'z transaksiyasida kommit qiladi.
"""

import threading
from datetime import time, timedelta
from types import SimpleNamespace

import pytest
from django.db import connections
from django.utils import timezone

from apps.accounts.factories import UserFactory
from apps.accounts.models import User
from apps.barbers.factories import BarberProfileFactory
from apps.bookings.models import Appointment
from apps.bookings.services import appointments as appt_service
from apps.bookings.services.exceptions import SlotUnavailable
from apps.schedule.factories import WorkScheduleFactory
from apps.services.factories import ServiceFactory

pytestmark = pytest.mark.django_db(transaction=True)

THREADS = 10


@pytest.fixture
def race_env():
    barber = BarberProfileFactory(is_active_now=True)
    day = timezone.localdate() + timedelta(days=1)
    WorkScheduleFactory(
        barber=barber, weekday=day.weekday(), start_time=time(9, 0), end_time=time(18, 0)
    )
    service = ServiceFactory(barber=barber, duration_min=30)
    users = [UserFactory(role=User.Role.CLIENT) for _ in range(THREADS)]
    return SimpleNamespace(barber=barber, day=day, service=service, users=users)


def test_ten_threads_one_winner(race_env):
    """10 parallel create_appointment -> 1 muvaffaqiyat, 9 SlotUnavailable."""
    barrier = threading.Barrier(THREADS)
    results: list = [None] * THREADS

    def worker(index: int) -> None:
        try:
            barrier.wait(timeout=15)
            appt_service.create_appointment(
                client=race_env.users[index],
                barber=race_env.barber,
                service=race_env.service,
                day=race_env.day,
                start_time=time(10, 0),
            )
            results[index] = "ok"
        except SlotUnavailable:
            results[index] = "slot_unavailable"
        except Exception as exc:  # noqa: BLE001 — xato testda ko'rinib turishi kerak
            results[index] = exc
        finally:
            connections.close_all()  # har thread o'z ulanishini yopadi

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(THREADS)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    unexpected = [(i, r) for i, r in enumerate(results) if r not in ("ok", "slot_unavailable")]
    assert not unexpected, f"Kutilmagan xatolar: {unexpected}"

    assert results.count("ok") == 1
    assert results.count("slot_unavailable") == THREADS - 1

    assert (
        Appointment.objects.filter(
            barber=race_env.barber, date=race_env.day, start_time=time(10, 0)
        ).count()
        == 1
    )
