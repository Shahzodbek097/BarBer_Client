"""Qo'lda eslatma yuborish (dev/demo va Beat qo'llab tushishi uchun)."""

from datetime import date

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.telegram.services.reminders import send_reminders_for


class Command(BaseCommand):
    help = "Berilgan kun tasdiqlangan navbatlariga eslatma (Telegram, bo'lmasa SMS)"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--day",
            default=None,
            help="Sana YYYY-MM-DD ko'rinishida (default: bugun)",
        )

    def handle(self, *args, **options) -> None:
        day = date.fromisoformat(options["day"]) if options["day"] else timezone.localdate()
        sent = send_reminders_for(day)
        self.stdout.write(self.style.SUCCESS(f"{sent} eslatma yuborildi ({day})."))
