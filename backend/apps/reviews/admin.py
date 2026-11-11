"""Admin: baholar."""

from django.contrib import admin

from apps.reviews.models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("barber", "client", "rating", "is_visible", "created_at")
    list_filter = ("rating", "is_visible")
    search_fields = ("client__phone", "barber__user__full_name", "comment")
    list_select_related = ("client", "barber__user")
    list_editable = ("is_visible",)
