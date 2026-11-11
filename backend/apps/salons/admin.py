"""Admin: sartaroshxona."""

from django.contrib import admin

from apps.salons.models import Salon


@admin.register(Salon)
class SalonAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "owner",
        "region",
        "district",
        "status",
        "rating_avg",
        "is_deleted",
        "created_at",
    )
    list_filter = ("status", "region")
    search_fields = ("name", "slug", "owner__phone", "address")
    list_select_related = ("owner", "region", "district")
    list_editable = ("status", "is_deleted")
    readonly_fields = ("slug", "rating_avg", "rating_count", "created_at", "updated_at")
