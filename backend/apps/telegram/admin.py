"""Telegram admin (chat bog'lanishlari va kodlar)."""

from django.contrib import admin

from apps.telegram.models import LinkCode, TelegramChat


@admin.register(TelegramChat)
class TelegramChatAdmin(admin.ModelAdmin):
    list_display = ("user", "chat_id", "username", "is_active", "linked_at")
    list_filter = ("is_active",)
    search_fields = ("user__phone", "user__full_name", "username", "chat_id")
    readonly_fields = ("linked_at",)


@admin.register(LinkCode)
class LinkCodeAdmin(admin.ModelAdmin):
    list_display = ("user", "code", "created_at", "expires_at", "used_at")
    readonly_fields = ("code", "created_at", "expires_at", "used_at")
