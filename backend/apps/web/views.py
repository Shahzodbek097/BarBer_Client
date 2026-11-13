"""Veb sahifa viewlari — logikasiz TemplateView (bosqich 6).

Har bir sahifa bo'sh skelet: ma'lumotlarni brauzerdagi JS REST API'dan
(`/api/v1/...`) JWT bilan yuklaydi. Role kabinetlari faqat skelet qaytaradi —
JS foydalanuvchi roliga qarab yo'naltiradi/ko'rsatadi.
"""

from django.views.generic import TemplateView


class PageView(TemplateView):
    """Barcha sahifalar uchun umumiy asos: `page_name` ni contextga qo'yadi."""

    page_name = ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_name"] = self.page_name
        return context


class IndexView(PageView):
    """`/` — ochiq katalog: salonlar ro'yxati."""

    template_name = "web/index.html"
    page_name = "catalog"


class SalonDetailView(PageView):
    """`/salon/{id}/` — salon sahifasi: sartaroshlar."""

    template_name = "web/salon.html"
    page_name = "salon"


class BarberDetailView(PageView):
    """`/barber/{id}/` — sartarosh sahifasi: xizmatlar, slotlar, navbat olish."""

    template_name = "web/barber.html"
    page_name = "barber"


class AuthView(PageView):
    """`/auth/` — kirish / ro'yxatdan o'tish (OTP)."""

    template_name = "web/auth.html"
    page_name = "auth"


class ClientBookingsView(PageView):
    """`/c/` — mijoz kabineti: navbatlarim."""

    template_name = "web/client.html"
    page_name = "client"


class BarberCabinetView(PageView):
    """`/barber/` (faqat bu yo'l — detail bilan adashmaslik uchun url'da aniq)."""

    template_name = "web/barber_cabinet.html"
    page_name = "barber-cabinet"


class BarberProfileView(PageView):
    """`/barber/profile/` — profil, xizmatlar, jadval."""

    template_name = "web/barber_profile.html"
    page_name = "barber-profile"


class SalonCabinetView(PageView):
    """`/salon/` (detail `/salon/{id}/` bilan birga)."""

    template_name = "web/salon_cabinet.html"
    page_name = "salon-cabinet"


class AdminPanelView(PageView):
    """`/panel/` — super admin: moderatsiya + statistika."""

    template_name = "web/panel.html"
    page_name = "panel"


class NotificationsView(PageView):
    """`/notifications/` — xabarnomalar ro'yxati."""

    template_name = "web/notifications.html"
    page_name = "notifications"
