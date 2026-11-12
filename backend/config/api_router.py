"""API v1 router (bosqich 5).

Barcha REST endpointlar shu yerda to'planadi (auth bundan tashqari —
`apps.accounts.api.urls` config/urls.py'da alohida ulangan).
"""

from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.barbers.api.views import (
    BarberProfileView,
    BarberServiceViewSet,
    BarberStatusView,
    BreakViewSet,
    DayOffViewSet,
    WeekScheduleView,
)
from apps.bookings.api.catalog import BarberViewSet, RegionViewSet, SalonViewSet
from apps.bookings.api.views import BookingViewSet
from apps.notifications.api.views import NotificationViewSet
from apps.reviews.api.views import BarberReviewsView, ReviewCreateView
from apps.salons.api.views import SalonBarbersView, SalonProfileView
from config.api_admin import (
    AdminSalonApproveView,
    AdminSalonBlockView,
    AdminSalonListView,
    AdminStatsView,
)

router = DefaultRouter()
router.register("catalog/regions", RegionViewSet, basename="catalog-regions")
router.register("catalog/salons", SalonViewSet, basename="catalog-salons")
router.register("catalog/barbers", BarberViewSet, basename="catalog-barbers")
router.register("bookings", BookingViewSet, basename="bookings")
router.register("barber/services", BarberServiceViewSet, basename="barber-services")
router.register("barber/schedule/breaks", BreakViewSet, basename="barber-breaks")
router.register("barber/day-offs", DayOffViewSet, basename="barber-day-offs")
router.register("notifications", NotificationViewSet, basename="notifications")

custom_urls = [
    # Sartarosh kabineti
    path("barber/profile/", BarberProfileView.as_view()),
    path("barber/schedule/", WeekScheduleView.as_view()),
    path("barber/status/", BarberStatusView.as_view()),
    # Salon egasi
    path("salon/profile/", SalonProfileView.as_view()),
    path("salon/barbers/", SalonBarbersView.as_view()),
    # Sharhlar
    path("reviews/", ReviewCreateView.as_view()),
    path("reviews/barber/<int:barber_id>/", BarberReviewsView.as_view()),
    # Super admin
    path("admin/salons/", AdminSalonListView.as_view()),
    path("admin/salons/<int:pk>/approve/", AdminSalonApproveView.as_view()),
    path("admin/salons/<int:pk>/block/", AdminSalonBlockView.as_view()),
    path("admin/stats/", AdminStatsView.as_view()),
]

urlpatterns = router.urls + custom_urls
