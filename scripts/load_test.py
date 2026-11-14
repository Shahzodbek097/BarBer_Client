"""Yuk testi (bosqich 8): katalog/sahifa endpointlariga parallel so'rovlar.

Gate: umumiy p95 < 500 ms.

Foydalanish:
    python scripts/load_test.py --url http://localhost:8000 --users 20 --requests 240

Chiqadi: har endpoint uchun o'rtacha / p50 / p95 / p99 / xatolar, so'ng
umumiy p95 va gate hukmi (exit code 0 = o'tdi, 1 = o'tmadi).
"""

from __future__ import annotations

import argparse
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from statistics import mean

import requests

DEFAULT_URL = "http://localhost:8000"

# Windows konsol (cp1251) emoji'larni yoqolmaydi
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def percentile(sorted_ms: list[float], p: float) -> float:
    """Nearest-rank persentil (sorted_ms taxmin qilinadi)."""
    if not sorted_ms:
        return 0.0
    idx = max(0, min(len(sorted_ms) - 1, round(p * (len(sorted_ms) - 1))))
    return sorted_ms[idx]


def discover(url: str) -> list[tuple[str, str]]:
    """Mavjud salon/sartarosh idlarini topib, dinamik endpointlar qo'shadi."""
    dynamic: list[tuple[str, str]] = []
    try:
        salons = requests.get(f"{url}/api/v1/catalog/salons/", timeout=10).json()
        rows = salons.get("results", salons)
        if rows:
            dynamic.append(("salon_page", f"/salon/{rows[0]['id']}/"))
        barbers = requests.get(f"{url}/api/v1/catalog/barbers/", timeout=10).json()
        rows = barbers.get("results", barbers)
        if rows:
            dynamic.append(("barber_page", f"/barber/{rows[0]['id']}/"))
            dynamic.append(("barber_services", f"/api/v1/catalog/barbers/{rows[0]['id']}/services/"))
    except Exception:  # noqa: BLE001 — katalog bo'sh bo'lsa ham asosiy test ishlaydi
        pass
    return dynamic


def main() -> int:
    parser = argparse.ArgumentParser(description="BarBer yuk testi (p95 gate)")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--users", type=int, default=20, help="parallel ishchilar")
    parser.add_argument("--requests", type=int, default=240, help="jami so'rovlar")
    args = parser.parse_args()

    base = args.url.rstrip("/")
    endpoints = [
        ("health", "/health/"),
        ("home", "/"),
        ("regions", "/api/v1/catalog/regions/"),
        ("salons", "/api/v1/catalog/salons/"),
        ("barbers", "/api/v1/catalog/barbers/"),
        *discover(base),
    ]
    print(f"Maqsad: {base} | ishchilar: {args.users} | so'rovlar: {args.requests}")
    print("Endpointlar:", ", ".join(name for name, _ in endpoints))

    # Har ishchiga o'z sessiyasi (ulanishlarni qayta ishlatadi)
    local = threading.local()

    def worker(index: int) -> list[tuple[str, float, int]]:
        if not hasattr(local, "session"):
            local.session = requests.Session()
        session: requests.Session = local.session
        results: list[tuple[str, float, int]] = []
        # ishchilar turli endpointlarni aralashtirib oladi
        count = args.requests // args.users
        for i in range(count):
            name, path = endpoints[(index + i) % len(endpoints)]
            start = time.perf_counter()
            try:
                resp = session.get(f"{base}{path}", timeout=15)
                code = resp.status_code
            except requests.RequestException:
                code = 0
            results.append((name, (time.perf_counter() - start) * 1000, code))
        return results

    print("Yuk yuborilmoqda...", flush=True)
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.users) as pool:
        chunks = list(pool.map(worker, range(args.users)))
    elapsed = time.perf_counter() - started

    merged: list[tuple[str, float, int]] = [row for chunk in chunks for row in chunk]
    all_ms = sorted(ms for _, ms, _ in merged)
    failed = [(name, code) for name, _, code in merged if code != 200]

    print(f"\nJami: {len(merged)} so'rov, {elapsed:.1f}s, "
          f"throughput {len(merged) / elapsed:.0f} req/s")
    print(f"{'endpoint':<16}{'n':>5}{'ort':>9}{'p50':>9}{'p95':>9}{'p99':>9}{'xato':>6}")
    print("-" * 63)
    for name, _ in endpoints:
        ms = sorted(m for n, m, _ in merged if n == name)
        if not ms:
            continue
        errors = sum(1 for n, _, c in merged if n == name and c != 200)
        print(f"{name:<16}{len(ms):>5}{mean(ms):>9.0f}{percentile(ms, .5):>9.0f}"
              f"{percentile(ms, .95):>9.0f}{percentile(ms, .99):>9.0f}{errors:>6}")

    p95_all = percentile(all_ms, 0.95)
    print("-" * 63)
    print(f"Umumiy p95: {p95_all:.0f} ms | xatolar: {len(failed)}")

    gate_ok = p95_all < 500 and not failed
    verdict = "O'TDI ✅" if gate_ok else "O'TMADI ❌"
    print(f"GATE (p95 < 500 ms va xatosiz): {verdict}")
    return 0 if gate_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
