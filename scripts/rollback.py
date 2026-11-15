"""Rollback skripti (bosqich 9): oldingi deploy'ga qaytish.

Ishlatilishi (repo ildizidan):
  1) Har muvaffaqiyatli deploy'dan keyin:
       python scripts/rollback.py --record
     → hozirgi commit SHA'i `backups/last_deploy.txt`ga yoziladi
  2) Muammo bo'lsa:
       python scripts/rollback.py --to HEAD~1
       python scripts/rollback.py --to <sha> --db-rollback bookings 0001
     → koddagi sha checkout, prod image rebuild, stack restart,
       health tekshiruvi; --db-rollback berilsa migratsiya ham orqaga.

Eslatma: rollback working tree'ni detach qiladi (`git checkout <sha>`).
`main`ga qaytish: git checkout main. Bazani oldinga siljitish (migratsiya
bekor qilish) ma'lumot yo'qotishi mumkin — birinchi navbatda zaxira oling:
python scripts/backup_db.py
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BACKUPS = REPO / "backups"
RECORD = BACKUPS / "last_deploy.txt"
COMPOSE = [
    "docker", "compose", "-f", "docker/docker-compose.prod.yml",
]

# Windows konsol (cp1251) emoji/panja belgilarini yo'qolmaydi
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO, check=True, capture_output=True, text=True
    ).stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Prod rollback")
    parser.add_argument("--record", action="store_true", help="hozirgi SHA'ni deploy sifatida yozish")
    parser.add_argument("--to", help="qaytish target: SHA, tag, HEAD~1, yoki last_deploy")
    parser.add_argument("--db-rollback", nargs=2, metavar=("APP", "MIGRATSIYA"))
    parser.add_argument("--port", type=int, default=8000, help="web port (default 8000)")
    args = parser.parse_args()

    BACKUPS.mkdir(exist_ok=True)

    if args.record:
        current = git("rev-parse", "HEAD")
        RECORD.write_text(current, encoding="utf-8")
        print(f"Deploy yozildi: {current}")
        return 0

    if not args.to:
        parser.error("yoki --record, yoki --to (masalan --to last_deploy yoki --to HEAD~1)")

    target = (
        RECORD.read_text(encoding="utf-8").strip()
        if args.to == "last_deploy"
        else args.to
    )
    previous_head = git("rev-parse", "HEAD")

    # oldingi SHA'ni qayta qo'yish uchun saqlab qo'yamiz (re-forward uchun)
    BACKUPS.joinpath("rolled_back_from.txt").write_text(previous_head, encoding="utf-8")

    print(f"Rollback: {previous_head[:8]} → {target}")
    git("checkout", "--detach", target)

    try:
        subprocess.run([*COMPOSE, "up", "-d", "--build"], cwd=REPO, check=True)
    except subprocess.CalledProcessError:
        git("checkout", "--detach", previous_head)
        print("XATO: build/up muvaffaqiyatsiz — oldingi holatga qaytarildi.")
        return 1

    if args.db_rollback:
        app, migration = args.db_rollback
        print(f"DB rollback: {app} → {migration}")
        subprocess.run(
            [
                "docker", "exec", "barber_prod_web",
                "python", "manage.py", "migrate", app, migration, "--noinput",
            ],
            check=True,
        )

    # health tekshiruvi (3 daqiqa)
    url = f"http://localhost:{args.port}/health/"
    deadline = time.time() + 180
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                if resp.status == 200:
                    print(f"Rollback tayyor — {url} 200 OK")
                    return 0
        except Exception:  # noqa: BLE001 — health kelmagunicha kutamiz
            pass
        time.sleep(5)
    print("XATO: health 3 daqiqada o'zgartirilmadi — konteyner log'larini tekshiring.")
    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"XATO: {exc}")
        sys.exit(1)
