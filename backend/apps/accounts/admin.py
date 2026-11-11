"""Admin: foydalanuvchi va OTP kodlari."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.accounts.models import OTPCode, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Kastom user admin: username o'rniga telefon."""

    ordering = ("-date_joined",)
    list_display = (
        "phone",
        "full_name",
        "role",
        "is_verified",
        "is_blocked",
        "is_active",
        "date_joined",
    )
    list_filter = ("role", "is_verified", "is_blocked", "lang", "is_active")
    search_fields = ("phone", "full_name")
    list_editable = ("is_verified", "is_blocked")
    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        ("Shaxsiy", {"fields": ("full_name", "avatar", "lang")}),
        ("Rol va holat", {"fields": ("role", "is_verified", "is_blocked")}),
        (
            "Ruxsatlar",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        ("Muhim sanalar", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("phone", "full_name", "role", "password1", "password2"),
            },
        ),
    )


@admin.register(OTPCode)
class OTPCodeAdmin(admin.ModelAdmin):
    list_display = (
        "phone",
        "purpose",
        "attempts",
        "is_used",
        "expires_at",
        "created_at",
    )
    list_filter = ("purpose", "is_used")
    search_fields = ("phone",)
    readonly_fields = ("code_hash", "created_at")
