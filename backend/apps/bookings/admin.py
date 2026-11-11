"""Admin: navbat va tarix."""

from django.contrib import admin

from apps.bookings.models import Appointment, AppointmentHistory


class AppointmentHistoryInline(admin.TabularInline):
    model = AppointmentHistory
    extra = 0
    can_delete = False
    readonly_fields = ("old_status", "new_status", "changed_by", "comment", "at")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "client",
        "barber",
        "service",
        "date",
        "start_time",
        "status",
        "source",
        "price",
    )
    list_filter = ("status", "source", "date")
    search_fields = ("client__phone", "client__full_name", "barber__user__full_name")
    list_select_related = ("client", "barber__user", "service", "salon")
    date_hierarchy = "date"
    inlines = (AppointmentHistoryInline,)


@admin.register(AppointmentHistory)
class AppointmentHistoryAdmin(admin.ModelAdmin):
    """Tarix — faqat o'qish (holat o'zgarishlari service qatlamidan yoziladi)."""

    list_display = ("appointment", "old_status", "new_status", "changed_by", "at")
    list_filter = ("new_status",)
    list_select_related = ("appointment", "changed_by")
    readonly_fields = (
        "appointment",
        "old_status",
        "new_status",
        "changed_by",
        "comment",
        "at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
