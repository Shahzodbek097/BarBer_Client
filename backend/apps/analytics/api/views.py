"""Hisobot API (bosqich 7): kunlik/davriy JSON va Excel eksport.

Rol izolyatsiyasi: sartarosh faqat o'z ma'lumoti, salon egasi faqat
o'z saloni, super admin hammasi (`IsBarber/IsSalonAdmin/IsSuperAdmin`).
`?format=xlsx` bo'lsa fayl yuklab olinadi.
"""

from datetime import date

from django.utils import timezone
from rest_framework import status as http_status
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsBarber, IsSalonAdmin, IsSuperAdmin
from apps.analytics.services import reports
from apps.analytics.services.xlsx import XLSXRenderer, xlsx_response

REPORT_STATUS_LABELS = {
    "pending": "Kutilmoqda",
    "confirmed": "Tasdiqlangan",
    "completed": "Bajarildi",
    "rejected": "Rad etildi",
    "cancelled": "Bekor qilindi",
    "no_show": "Kelmadi",
}


def _parse_day(value: str | None, default: date) -> date:
    if not value:
        return default
    try:
        return date.fromisoformat(value)
    except ValueError:
        return default


def _parse_range(query) -> tuple[date, date]:
    today = timezone.localdate()
    start = _parse_day(query.get("from"), today.replace(day=1))
    end = _parse_day(query.get("to"), today)
    if end < start:
        start, end = end, start
    return start, end


class BarberDailyReportView(APIView):
    """Sartarosh kunlik hisoboti (JSON yoki Excel)."""

    permission_classes = [IsAuthenticated, IsBarber]
    renderer_classes = [JSONRenderer, XLSXRenderer]

    def get(self, request) -> Response:
        day = _parse_day(request.query_params.get("day"), timezone.localdate())
        report = reports.barber_daily(request.user.barber_profile, day)
        if request.query_params.get("format") == "xlsx":
            rows = [
                [
                    row["time"],
                    row["client"],
                    row["service"],
                    REPORT_STATUS_LABELS.get(row["status"], row["status"]),
                    row["price"],
                    row["source"],
                ]
                for row in report["rows"]
            ]
            return xlsx_response(
                "Kunlik hisobot",
                ["Vaqt", "Mijoz", "Xizmat", "Holat", "Narx (UZS)", "Manba"],
                rows,
                f"barber-report-{day.isoformat()}.xlsx",
                totals=["", "", "", "Daromad:", report["totals"]["revenue"], ""],
            )
        return Response(report)


class SalonReportView(APIView):
    """Salon egasi davri hisoboti (default: shu oy boshidan bugunga)."""

    permission_classes = [IsAuthenticated, IsSalonAdmin]
    renderer_classes = [JSONRenderer, XLSXRenderer]

    def get(self, request) -> Response:
        start, end = _parse_range(request.query_params)
        salon = request.user.salons.first()
        if salon is None:
            return Response({"detail": "Salon topilmadi."}, status=http_status.HTTP_404_NOT_FOUND)
        report = reports.salon_period(salon, start, end)
        if request.query_params.get("format") == "xlsx":
            rows = [
                [row["barber"], row["total"], row["completed"], row["revenue"]]
                for row in report["rows"]
            ]
            return xlsx_response(
                "Salon hisoboti",
                ["Sartarosh", "Navbatlar", "Bajarilgan", "Daromad (UZS)"],
                rows,
                f"salon-report-{start.isoformat()}_{end.isoformat()}.xlsx",
                totals=[
                    "Jami",
                    report["totals"]["total"],
                    report["totals"]["completed"],
                    report["totals"]["revenue"],
                ],
            )
        return Response(report)


class AdminReportView(APIView):
    """Super admin davri hisoboti (salonlar bo'yicha)."""

    permission_classes = [IsAuthenticated, IsSuperAdmin]
    renderer_classes = [JSONRenderer, XLSXRenderer]

    def get(self, request) -> Response:
        start, end = _parse_range(request.query_params)
        report = reports.admin_period(start, end)
        if request.query_params.get("format") == "xlsx":
            rows = [
                [row["salon"], row["total"], row["completed"], row["revenue"]]
                for row in report["rows"]
            ]
            return xlsx_response(
                "Umumiy hisobot",
                ["Salon", "Navbatlar", "Bajarilgan", "Daromad (UZS)"],
                rows,
                f"admin-report-{start.isoformat()}_{end.isoformat()}.xlsx",
                totals=[
                    "Jami",
                    report["totals"]["total"],
                    report["totals"]["completed"],
                    report["totals"]["revenue"],
                ],
            )
        return Response(report)
