"""Bazani zaxiralash (bosqich 9): pg_dump custom format → backups/.

Foydalanish (repo ildizidan, host'da docker CLI kerak):
    python scripts/backup_db.py                      # prod stack (barber_prod_db)
    python scripts/backup_db.py --container barber_db --db barber_client

Natija: backups/barber_client_<sana>_<vaqt>.dump (pg_restore bilan tiklanadi).
Eski zaxiralar: --keep N (default 14) — eng yangilari qoladi.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BACKUPS = REPO / "backups"

# Windows konsol (cp1251) emoji/panja belgilarini yo'qolmaydi
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser(description="Postgres zaxira (pg_dump -Fc)")
    parser.add_argument("--container", default="barber_prod_db")
    parser.add_argument("--db", default="barber_client")
    parser.add_argument("--user", default="barber")
    parser.add_argument("--keep", type=int, default=14)
    args = parser.parse_args()

    BACKUPS.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = BACKUPS / f"{args.db}_{stamp}.dump"

    print(f"Zaxira: {args.container}/{args.db} → {target.name}")
    result = subprocess.run(
        ["docker", "exec", args.container, "pg_dump", "-U", args.user, "-Fc", args.db],
        capture_output=True,
        check=True,
    )
    target.write_bytes(result.stdout)
    size_kb = target.stat().st_size / 1024
    print(f"Yozildi: {size_kb:.0f} KB")

    # Eski zaxiralarni tozalash (eng yangi N ta qoladi)
    dumps = sorted(BACKUPS.glob(f"{args.db}_*.dump"))
    for old in dumps[: -args.keep] if len(dumps) > args.keep else []:
        old.unlink()
        print("O'chirildi (eski):", old.name)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"XATO: pg_dump chiqdi {exc.returncode}: {exc.stderr.decode(errors='replace')}")
        sys.exit(1)
