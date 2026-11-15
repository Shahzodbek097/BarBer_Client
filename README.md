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
│   ├── config/         # settings/dev|test|prod, urls, asgi, celery
│   ├── apps/           # 10 modul: core, accounts, salons, barbers, services,
│   │                   # schedule, bookings, notifications, reviews, analytics
│   └── requirements/   # base / dev / prod
├── frontend/           # SPA kabinetlar (6-bosqichda)
├── templates/          # SSR katalog sahifalari (6-bosqichda)
├── docker/             # Dockerfile'lar va compose fayllar
├── scripts/            # yordamchi skriptlar
└── docs/               # hujjatlar (10-bosqichda to'ldiriladi)
```

---

## Tez boshlash

### 1-usul: Docker orqali (tavsiya — 1 buyruq)

```bash
cp .env.example .env            # Windows: copy .env.example .env
docker compose -f docker/docker-compose.dev.yml up -d --build
```

→ http://localhost:8000/health/ — `{"status": "ok"}` qaytarsa, hammasi ishlayapti.

### 2-usul: Lokal (venv) + Docker'da faqat infrastruktura

```bash
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r backend/requirements/dev.txt
copy .env.example .env

docker compose -f docker/docker-compose.dev.yml up -d db redis   # faqat DB+Redis
python backend\manage.py migrate
python backend\manage.py loaddata regions      # 14 viloyat / 53 tuman
python backend\manage.py runserver
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
- [ ] Bosqich 10 — Hujjatlashtirish

Muallif: BarBer_Client jamoasi
