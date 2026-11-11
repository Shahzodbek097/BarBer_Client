"""Admin: hududlar va audit jurnali."""

from django.contrib import admin

from apps.core.models import AuditLog, District, Region


class DistrictInline(admin.TabularInline):
    model = District
    extra = 0


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    list_editable = ("is_active",)
    search_fields = ("name",)
    inlines = (DistrictInline,)


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ("name", "region", "is_active")
    list_filter = ("region",)
    list_select_related = ("region",)
    search_fields = ("name", "region__name")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Audit jurnali — ma'lumot butunligi uchun faqat o'qish."""

    list_display = ("action", "model_name", "object_id", "actor", "at")
    list_filter = ("action", "model_name")
    search_fields = ("action", "model_name", "object_id")
    readonly_fields = ("actor", "action", "model_name", "object_id", "payload", "at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
