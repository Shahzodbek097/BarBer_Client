#!/usr/bin/env python
"""Django buyruq-satir utilitasi."""

import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django topilmadi yoki import qilib bo'lmadi. "
            "Muhrni faollashtirganingizni va Django o'rnatilganini tekshiring: "
            "pip install -r requirements/dev.txt"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
