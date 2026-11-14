"""Hisobot xizmatlari (bosqich 7).

Plan qoidasi: analytics bookings modellarini FAQAT O'QIYDI.
Daromad = bandlov paytida muzlatilgan `price` yig'indisi, faqat
COMPLETED navbatlar hisoblanadi (bekor/rad qilinganlar pul emas).
"""

from datetime import date
from decimal import Decimal

from django.db.models import Count, Q, Sum

from apps.bookings.models import Appointment, AppointmentStatus

REVENUE_STATUSES = (AppointmentStatus.COMPLETED,)


def _money(value) -> Decimal:
    return Decimal(value or 0)


def barber_daily(barber, day: date) -> dict:
    """Sartarosh kunlik hisoboti: ro'yxat + holat kesim + daromad."""
    appts = list(
        Appointment.objects.filter(barber=barber, date=day)
        .select_related("client", "service")
        .order_by("start_time")
    )
    revenue = sum(
        (_money(a.price) for a in appts if a.status in REVENUE_STATUSES),
        Decimal("0"),
    )
    return {
        "day": day.isoformat(),
        "barber": {
            "id": barber.pk,
            "name": barber.user.full_name,
            "salon": barber.salon.name if barber.salon_id else None,
        },
        "rows": [
            {
                "time": a.start_time.isoformat()[:5],
                "client": a.client.full_name,
                "service": a.service.name,
                "status": a.status,
                "price": a.price,
                "source": a.source,
            }
            for a in appts
        ],
        "totals": {
            "all": len(appts),
            "by_status": {
                status: sum(1 for a in appts if a.status == status)
                for status in AppointmentStatus.values
            },
            "revenue": revenue,
        },
    }


def salon_period(salon, start: date, end: date) -> dict:
    """Salon davri hisoboti: sartaroshlar bo'yicha guruhlangan yig'indilar."""
    grouped = (
        Appointment.objects.filter(barber__salon=salon, date__range=(start, end))
        .values("barber_id", "barber__user__full_name")
        .annotate(
            total=Count("id"),
            completed=Count("id", filter=Q(status__in=REVENUE_STATUSES)),
            revenue=Sum("price", filter=Q(status__in=REVENUE_STATUSES)),
        )
        .order_by("barber__user__full_name")
    )
    rows = [
        {
            "barber_id": row["barber_id"],
            "barber": row["barber__user__full_name"],
            "total": row["total"],
            "completed": row["completed"],
            "revenue": _money(row["revenue"]),
        }
        for row in grouped
    ]
    totals = {
        "total": sum(r["total"] for r in rows),
        "completed": sum(r["completed"] for r in rows),
        "revenue": sum((r["revenue"] for r in rows), Decimal("0")),
    }
    return {
        "from": start.isoformat(),
        "to": end.isoformat(),
        "salon": {"id": salon.pk, "name": salon.name, "status": salon.status},
        "rows": rows,
        "totals": totals,
    }


def admin_period(start: date, end: date) -> dict:
    """Super admin davri hisoboti: tasdiqlangan salonlar bo'yicha."""
    from apps.salons.models import Salon, SalonStatus  # noqa: PLC0415 — izolyatsiya uchun lokal

    salons = Salon.objects.filter(status=SalonStatus.APPROVED).order_by("name")
    rows = []
    for salon in salons:
        agg = Appointment.objects.filter(barber__salon=salon, date__range=(start, end)).aggregate(
            total=Count("id"),
            completed=Count("id", filter=Q(status__in=REVENUE_STATUSES)),
            revenue=Sum("price", filter=Q(status__in=REVENUE_STATUSES)),
        )
        rows.append(
            {
                "salon_id": salon.pk,
                "salon": salon.name,
                "total": agg["total"],
                "completed": agg["completed"],
                "revenue": _money(agg["revenue"]),
            }
        )
    return {
        "from": start.isoformat(),
        "to": end.isoformat(),
        "rows": rows,
        "totals": {
            "total": sum(r["total"] for r in rows),
            "completed": sum(r["completed"] for r in rows),
            "revenue": sum((r["revenue"] for r in rows), Decimal("0")),
        },
    }
