"""Sartarosh ish jadvali: haftalik jadval, tanaffuslar, dam olish kunlari.

Bu modellar bosqich 4-dagi slot dvigatelining asosiy kirish ma'lumotlari.
"""

from django.db import models
from django.db.models import F, Q


class Weekday(models.IntegerChoices):
    MONDAY = 0, "Dushanba"
    TUESDAY = 1, "Seshanba"
    WEDNESDAY = 2, "Chorshanba"
    THURSDAY = 3, "Payshanba"
    FRIDAY = 4, "Juma"
    SATURDAY = 5, "Shanba"
    SUNDAY = 6, "Yakshanba"


class WorkSchedule(models.Model):
    """Sartaroshning haftalik jadvali: bir hafta kuniga yozuv."""

    barber = models.ForeignKey(
        "barbers.BarberProfile",
        on_delete=models.CASCADE,
        related_name="work_schedules",
        verbose_name="Sartarosh",
    )
    weekday = models.PositiveSmallIntegerField("Hafta kuni", choices=Weekday.choices)
    start_time = models.TimeField("Ish boshlanishi")
    end_time = models.TimeField("Ish tugashi")
    is_working = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Ish jadvali"
        verbose_name_plural = "Ish jadvallari"
        ordering = ("barber", "weekday")
        constraints = [
            models.UniqueConstraint(
                fields=("barber", "weekday"), name="work_schedule_unique_weekday"
            ),
            models.CheckConstraint(
                condition=Q(start_time__lt=F("end_time")),
                name="work_schedule_time_order",
            ),
        ]

    def __str__(self):
        return f"{self.barber} — {self.get_weekday_display()} {self.start_time}-{self.end_time}"


class ScheduleBreak(models.Model):
    """Ish kunidagi tanaffus (masalan, tushlik 13:00-14:00)."""

    schedule = models.ForeignKey(
        WorkSchedule,
        on_delete=models.CASCADE,
        related_name="breaks",
        verbose_name="Jadval",
    )
    start_time = models.TimeField("Tanaffus boshlanishi")
    end_time = models.TimeField("Tanaffus tugashi")

    class Meta:
        verbose_name = "Tanaffus"
        verbose_name_plural = "Tanaffuslar"
        ordering = ("schedule", "start_time")
        constraints = [
            models.CheckConstraint(
                condition=Q(start_time__lt=F("end_time")),
                name="schedule_break_time_order",
            ),
        ]

    def __str__(self):
        return f"{self.schedule} ({self.start_time}–{self.end_time})"


class DayOff(models.Model):
    """Bir marta qo'yiladigan dam olish kuni (bayram, ta'til)."""

    barber = models.ForeignKey(
        "barbers.BarberProfile",
        on_delete=models.CASCADE,
        related_name="day_offs",
        verbose_name="Sartarosh",
    )
    date = models.DateField("Sana")
    reason = models.CharField("Sababi", max_length=200, blank=True, default="")

    class Meta:
        verbose_name = "Dam olish kuni"
        verbose_name_plural = "Dam olish kunlari"
        ordering = ("date",)
        constraints = [
            models.UniqueConstraint(fields=("barber", "date"), name="day_off_unique"),
        ]

    def __str__(self):
        return f"{self.barber} — {self.date}"
