"""Admin: sartarosh profili va sevimlilar.

Ish jadvali (WorkSchedule/DayOff) schedule app adminida boshqariladi —
app orasidagi import faqat yuqoriga (barbers ← schedule emas).
"""

from django.contrib import admin

from apps.barbers.models import BarberProfile, Favorite


@admin.register(BarberProfile)
class BarberProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "salon",
        "status",
        "is_active_now",
        "rating_avg",
        "experience_years",
    )
    list_filter = ("status", "is_active_now", "salon")
    search_fields = ("user__phone", "user__full_name")
    list_select_related = ("user", "salon")
    filter_horizontal = ("specialties",)


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("client", "barber", "created_at")
    search_fields = ("client__phone", "barber__user__phone")
    list_select_related = ("client", "barber__user")
