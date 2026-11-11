"""Admin: ish jadvali, tanaffuslar va dam olish kunlari."""

from django.contrib import admin

from apps.schedule.models import DayOff, ScheduleBreak, WorkSchedule


class ScheduleBreakInline(admin.TabularInline):
    model = ScheduleBreak
    extra = 0


@admin.register(WorkSchedule)
class WorkScheduleAdmin(admin.ModelAdmin):
    list_display = ("barber", "weekday", "start_time", "end_time", "is_working")
    list_filter = ("weekday", "is_working")
    list_select_related = ("barber__user",)
    inlines = (ScheduleBreakInline,)


@admin.register(ScheduleBreak)
class ScheduleBreakAdmin(admin.ModelAdmin):
    list_display = ("schedule", "start_time", "end_time")
    list_select_related = ("schedule__barber__user",)


@admin.register(DayOff)
class DayOffAdmin(admin.ModelAdmin):
    list_display = ("barber", "date", "reason")
    list_filter = ("date",)
    list_select_related = ("barber__user",)
