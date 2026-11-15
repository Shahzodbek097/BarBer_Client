# BarBer_Client 🧑‍🔧

Sartaroshxonalar va sartaroshlar uchun **onlayn navbat olish platformasi**.
Mijoz sartaroshni tanlaydi, bo'sh vaqtni ko'radi va navbat oladi; sartarosh o'z
shaxsiy kabinetida navbatlarni boshqaradi va kunlik tahlilni ko'radi.

- 📋 To'liq reja: `docs/PLAN.md`
- 🐍 Python 3.11 + Django 5.2 LTS + DRF
- 🗄 PostgreSQL 16 (+PostGIS) + Redis
- 🐳 Docker (dev: `db`, `redis`, `web`, `celery`)

---

## Loyiha strukturasi

```
BarBer_Client/
├── backend/            # Django (API + SSR)
│   ├── config/         # settings/base|dev|test|prod, urls, asgi, celery, api_router
│   └── apps/           # 12 modul: core, accounts, salons, barbers, services,
│   │                   # schedule, bookings, notifications, reviews, analytics,
│   │                   # telegram, web (UI — statik + template + JS)
│   └── requirements/   # base / dev
├── templates/          # SSR katalog sahifalari (root-level DIRS)
├── docker/             # Dockerfile (dev/prod) va compose fayllar
├── scripts/            # yuk testi, backup, restore drill, rollback
└── docs/               # PLAN.md, ARCHITECTURE.md, DEPLOY.md
```

Arxitektura qoidalar va oqimlar: **`docs/ARCHITECTURE.md`** ·
Deploy/operatsiyalar: **`docs/DEPLOY.md`**

---

## Yangi dasturchi testi — 30 daqiqada local ko'tarish

**0) Talablar (5 daq):** Git, Python 3.11, Docker Desktop ishga tushgan.

**1) Klone + env (2 daq):**

```bash
git clone <repo-url> && cd BarBer_Client
copy .env.example .env          # Windows; Linux/macOS: cp
```

**2) Dev stackni ko'tarish (10 daq — birinchi build pip yuklaydi):**

```bash
docker compose -f docker/docker-compose.dev.yml up -d --build
```

Konteyner startda migratsiya + viloyat fixture'ini o'zi bajaradi.

**3) Tekshirish ro'yxati (5 daq):**

| Tekshiruv | Muvaffaqiyat |
|---|---|
| http://localhost:8000/health/ | `{"status": "ok"}` |
| http://localhost:8000/ | Ochiq katalog: viloyat + salon kartalari |
| http://localhost:8000/api/docs/ | Swagger ochiladi (barcha endpointlar) |
| `docker compose -f docker/docker-compose.dev.yml logs web --tail 5` | gunicorn "Application startup complete" |

**4) Testlar (10 daq — venv'siz, konteyner ichida):**

```bash
docker compose -f docker/docker-compose.dev.yml exec web python -m pytest -q
```

→ 456 test, 0 xato bo'lishi kerak (coverage uchun: `--cov=apps`).

**5) Jonli oqimni sinash (8 daq):** Swagger'da `register/` → javobdagi
`debug_code`ni (dev'da SMS console'ga yoziladi) `verify-otp/`ga yuboring →
`access` token bilan `POST /bookings/` qiling.

### Alternativ: host venv (Docker'siz pytest uchun)

```bash
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r backend/requirements/dev.txt

docker compose -f docker/docker-compose.dev.yml up -d db redis   # faqat infrastruktura
cd backend
python manage.py migrate && python manage.py loaddata regions
python manage.py runserver          # yoki ..\..\.venv\Scripts\python.exe -m pytest
```

---

## Buyruqlar (repo ildizidan)

| Buyruq | Vazifa |
|--------|--------|
| `docker compose -f docker/docker-compose.dev.yml up -d` | Dev muhitni ko'tarish |
| `docker compose -f docker/docker-compose.dev.yml down` | To'xtatish |
| `.venv\Scripts\python.exe -m pytest` (backend ichida) | Testlar |
| `ruff check backend && ruff format --check backend` | Lint/format tekshiruvi |
| `.venv\Scripts\python.exe backend\manage.py check` | Django sozlamalar tekshiruvi |
| `.venv\Scripts\python.exe scripts\load_test.py --users 20 --requests 240` | Yuk testi (gate: p95 < 500 ms) |
| `.venv\Scripts\python.exe -m pip_audit -r backend\requirements\base.txt` | Dependensiya zaiflik skaneri |

> Dev `web` konteyneri prod-shaklida xizmat qiladi: `gunicorn` + 4 ta
> `uvicorn` ASGI worker (WebSocket ishlaydi). `runserver` yagona jarayon
> bo'lgani uchun yuk testi p95 516 ms chiqqan; gunicorn'da 242 ms.
>
> Compose project nomlari o'ziga xos: dev — `barber-dev`, prod —
> `barber-prod` (default nom ularni aralashtirib yuborar edi). Dev
> `pgdata` volümi `docker_pgdata` (eski nom) ga bog'langan — ma'lumotlar
> saqlanadi.

### Production (bosqich 9)

```powershell
# Repo ildizidan — majburiy sirlar bilan:
$env:SECRET_KEY = "<50+ tasodifiy belgi>"
$env:POSTGRES_PASSWORD = "<kuchli parol>"
$env:ALLOWED_HOSTS = "<domain yoki localhost>"
docker compose -f docker/docker-compose.prod.yml up -d --build

# Operatsiyalar (repo ildizidan):
python scripts/backup_db.py                 # pg_dump → backups/*.dump (14 ta saqlanadi)
python scripts/restore_drill.py --latest    # zaxira → scratch DB → jadval satrlari solishtirish
python scripts/rollback.py --record         # deploy paytida hozirgi SHA yoziladi
python scripts/rollback.py --to last_deploy # muammo bo'lsa: oldingi deploy'ga qaytish
```

TLS reverse proxy ortida: proxy `X-Forwarded-Proto: https` yuboradi,
`SECURE_SSL_REDIRECT` default 1 (lokal HTTP drill'da `0` beriladi).

> **pytest** yoki `manage.py` buyruqlarini backend papkasidan ishga tushirish qulay:
> `cd backend && ..\.venv\Scripts\python.exe -m pytest`

---

## Auth API (bosqich 3)

Barcha so'rovlar `/api/v1/auth/` prefiksi bilan, JSON formatda:

| Endpoint | Metod | Vazifa |
|----------|-------|--------|
| `register/` | POST | Ro'yxatdan o'tish (`phone`, `full_name`, `role`: client/barber/salon_admin) → SMS kod |
| `login/` | POST | Kirish (`phone`) → SMS kod |
| `verify-otp/` | POST | Kod tekshiruvi (`phone`, `purpose`: registration/login, `code`) → `access` + `refresh` + user |
| `refresh/` | POST | Access yangilash (`refresh`) — rotation + blacklist yoqilgan |
| `logout/` | POST | Chiqish (`refresh`) — token blacklist'ga tushadi (auth talab qilinadi) |
| `me/` | GET/PATCH | Joriy profil (Bearer); tahrir: `full_name`, `lang`, `avatar` |

Dev muhitda (`DEBUG=True` + `SMS_PROVIDER=console`) javobda `debug_code` qaytadi —
SMS o'rniga kodni to'g'ridan-to'g'ri ishlatish mumkin. `curl` misoli:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"phone": "+998901234567", "full_name": "Ali Valiyev", "role": "client"}'
```

---

## Bosqichlar holati

- [x] **Bosqich 1** — Loyiha karkasi va konfiguratsiya ✅
- [x] **Bosqich 2** — Ma'lumotlar bazasi va modellar ✅
- [x] **Bosqich 3** — Foydalanuvchilar va autentifikatsiya ✅ (137 test, coverage 99%)
- [x] **Bosqich 4** — Asosiy biznes mantiq (slot dvigateli, navbat tsikli) ✅ (224 test, race-test OK)
- [x] **Bosqich 5** — API va backend (REST + WebSocket) ✅ (334 test, coverage 99%, Swagger + WS push ishlaydi)
- [x] **Bosqich 6** — Frontend va dizayn ✅ (364 test, coverage 99%, responsive 360/768/1440, WS push jonli isbotlandi)
- [x] **Bosqich 7** — Hisobotlar, Telegram bot, eslatmalar ✅ (404 test, coverage 99%, Excel eksport + Telegram zanjiri + SMS fallback e2e isbotlandi)
- [x] **Bosqich 8** — Test va xavfsizlik ✅ (456 test, coverage 99%, IDOR 49 + E2E 3 oqim, yuk p95 242ms < 500ms, pip-audit 0 zaiflik)
- [x] **Bosqich 9** — Docker va production deploy ✅ (prod stack + backup→restore drill 32 jadval mos + rollback skripti; gunicorn/uvicorn prod server)
- [x] **Bosqich 10** — Hujjatlashtirish ✅ (ARCHITECTURE + DEPLOY kitobchasi, README "30 daqiqada" testi — frеsh clone'da jonli tekshirildi: health 43s, 456 test OK)

Muallif: BarBer_Client jamoasi
