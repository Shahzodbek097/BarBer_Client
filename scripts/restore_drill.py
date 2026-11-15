"""Zaxirani tiklash DRILL (bosqich 9): backup → yangi scratch DB → solishtirish.

Foydalanish (repo ildizidan):
    python scripts/restore_drill.py backups/barber_client_20261115_101500.dump
    python scripts/restore_drill.py --latest

Jarayon:
1. prod db konteynerida scratch bazasi yaratiladi (barber_restore_test)
2. dump pg_restore bilan scratch'ga tiklanadi
3. HAR jadval satr soni manba ↔ tiklangan bazada solishtiriladi
4. scratch bazasi va vaqtinchalik fayl o'chiriladi

Chiqish kodi 0 = drill o'tdi (barcha jadvallar mos).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BACKUPS = REPO / "backups"

# Windows konsol (cp1251) emoji/panja belgilarini yo'qolmaydi
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def docker_exec(container: str, *cmd: str, input_bytes: bytes | None = None) -> bytes:
    result = subprocess.run(
        ["docker", "exec", "-i", container, *cmd],
        capture_output=True,
        check=True,
        input=input_bytes,
    )
    return result.stdout


def psql(container: str, user: str, db: str, sql: str) -> None:
    """DROP DATABASE kabi tranzaksiyada ishlamaydiganlar uchun alohida -c."""
    docker_exec(container, "psql", "-U", user, "-d", db, "-c", sql)


def table_counts(container: str, user: str, db: str) -> dict[str, int]:
    """Har public jadval uchun count(*) — bitta psql sessiyasida."""
    sql = (
        "SELECT tablename FROM pg_tables WHERE schemaname='public';"
    )
    tables = docker_exec(
        container, "psql", "-U", user, "-d", db, "-Atc", sql
    ).decode().splitlines()
    counts: dict[str, int] = {}
    for table in tables:
        table = table.strip()
        if not table:
            continue
        value = docker_exec(
            container,
            "psql", "-U", user, "-d", db, "-Atc",
            f"SELECT count(*) FROM \"{table}\";",
        ).decode().strip()
        counts[table] = int(value or 0)
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description="Backup→restore drill")
    parser.add_argument("dump", nargs="?", help="backups/*.dump yo'li")
    parser.add_argument("--latest", action="store_true", help="eng yangi dump")
    parser.add_argument("--container", default="barber_prod_db")
    parser.add_argument("--user", default="barber")
    parser.add_argument("--source-db", default="barber_client")
    args = parser.parse_args()

    if args.latest:
        dumps = sorted(BACKUPS.glob("*.dump"))
        if not dumps:
            print("XATO: backups/ ichida .dump topilmadi — avval backup_db.py")
            return 1
        dump_path = dumps[-1]
    elif args.dump:
        dump_path = Path(args.dump)
    else:
        parser.error("yoki dump yo'li, yoki --latest")
        return 1
    if not dump_path.exists():
        print(f"XATO: fayl topilmadi: {dump_path}")
        return 1

    scratch = "barber_restore_test"
    container = args.container
    print(f"Drill: {dump_path.name} → {container}/{scratch}")

    # 1) scratch bazasi (eski drill qoldig'i tozalanadi) — DROP/CREATE
    # tranzaksiyada ishlamaydi, shuning uchun alohida psql chaqiruvlari
    psql(container, args.user, "postgres", f"DROP DATABASE IF EXISTS {scratch};")
    psql(container, args.user, "postgres", f"CREATE DATABASE {scratch};")

    # 2) dump'ni konteynerga ko'chirib tiklash
    subprocess.run(
        ["docker", "cp", str(dump_path), f"{container}:/tmp/drill.dump"],
        check=True,
        capture_output=True,
    )
    try:
        docker_exec(
            container,
            "pg_restore", "-U", args.user, "-d", scratch, "--no-owner",
            "/tmp/drill.dump",
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode(errors="replace")
        # pg_restore ba'zi warnings (misol: extensionlar) bilan ham tiklaydi
        if "error" not in stderr.lower() or "could not execute" not in stderr.lower():
            print("Ogohlantirishlar:\n" + stderr[-800:])
        else:
            print(f"XATO: pg_restore muvaffaqiyatsiz:\n{stderr[-1500:]}")
            return 1

    # 3) har jadval bo'yicha satr sonlari solishtiriladi
    source = table_counts(container, args.user, args.source_db)
    restored = table_counts(container, args.user, scratch)

    failures = sorted(set(source) | set(restored))
    failed = False
    print(f"{'jadval':<34}{'manba':>7}{'tikl.':>7}")
    for table in failures:
        s, r = source.get(table, -1), restored.get(table, -1)
        ok = s == r
        failed |= not ok
        print(f"{table:<34}{s:>7}{r:>7}{'' if ok else '  ← FARQ!'}")

    # 4) tozalash
    psql(container, args.user, "postgres", f"DROP DATABASE IF EXISTS {scratch};")
    docker_exec(container, "sh", "-c", "rm -f /tmp/drill.dump")

    print("DRILL: O'TDI ✅" if not failed else "DRILL: O'TMADI ❌")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
