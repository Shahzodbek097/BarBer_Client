"""Veb sahifa marshrutlari (bosqich 6).

Eslatma: `/barber/` kabinet va `/barber/{id}/` katalog sahifasi — ikki xil
shakl (int detail bilan mos kelmaydi). `/salon/` ham xuddi shunday.
"""

from django.urls import path

from apps.web import views

app_name = "web"

urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path("auth/", views.AuthView.as_view(), name="auth"),
    path("c/", views.ClientBookingsView.as_view(), name="client"),
    path("barber/", views.BarberCabinetView.as_view(), name="barber-cabinet"),
    path("barber/profile/", views.BarberProfileView.as_view(), name="barber-profile"),
    path("barber/<int:pk>/", views.BarberDetailView.as_view(), name="barber-detail"),
    path("salon/", views.SalonCabinetView.as_view(), name="salon-cabinet"),
    path("salon/<int:pk>/", views.SalonDetailView.as_view(), name="salon-detail"),
    path("panel/", views.AdminPanelView.as_view(), name="panel"),
    path("notifications/", views.NotificationsView.as_view(), name="notifications"),
]
