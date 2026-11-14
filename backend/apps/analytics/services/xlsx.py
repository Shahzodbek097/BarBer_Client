"""Excel eksport (openpyxl) — jadval → xlsx HttpResponse."""

from decimal import Decimal
from io import BytesIO

from django.http import HttpResponse
from openpyxl import Workbook
from rest_framework.renderers import BaseRenderer

XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class XLSXRenderer(BaseRenderer):
    """`?format=xlsx` so'rovini DRF muzokarasidan o'tkazadi.

    DRF `format` query param ko'rsa renderer'larni format bo'yicha filtrlaydi
    va mosi topilmasa Http404 ko'taradi — shuning uchun xlsx formatini
    ro'yxatdan o'tkazamiz. Asl fayl API qatlamida `xlsx_response()`
    (plain HttpResponse) orqali qaytadi, shuning uchun render()
    hech qachon chaqirilmaydi.
    """

    format = "xlsx"
    media_type = XLSX_CONTENT_TYPE

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return b""


def xlsx_response(
    sheet_title: str,
    header: list[str],
    rows: list[list],
    filename: str,
    totals: list | None = None,
) -> HttpResponse:
    """Oddiy jadval: sarlavha qatori, ma'lumot, (ixtiyoriy) jami qatori."""
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_title[:31]
    ws.append(header)
    for row in rows:
        ws.append([str(cell) if isinstance(cell, Decimal) else cell for cell in row])
    if totals:
        ws.append([])
        ws.append(totals)

    # ustun kengligini o'qish qulay qilish uchun
    for column_cells in ws.columns:
        width = max((len(str(c.value or "")) for c in column_cells), default=10)
        ws.column_dimensions[column_cells[0].column_letter].width = min(width + 2, 40)

    buffer = BytesIO()
    wb.save(buffer)
    response = HttpResponse(buffer.getvalue(), content_type=XLSX_CONTENT_TYPE)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
