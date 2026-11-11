"""Admin: xizmat kategoriyalari va xizmatlar."""

from django.contrib import admin

from apps.services.models import Service, ServiceCategory


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "order")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "owner_type",
        "barber",
        "salon",
        "category",
        "duration_min",
        "price",
        "is_active",
    )
    list_filter = ("owner_type", "category", "is_active")
    search_fields = ("name", "barber__user__full_name", "salon__name")
    list_select_related = ("barber__user", "salon", "category")
    list_editable = ("is_active",)
