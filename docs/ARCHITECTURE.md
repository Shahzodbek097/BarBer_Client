# BarBer_Client — Arxitektura

> Bu hujjat loyihaning ichki tuzilishini tushuntiradi: qatlamlar, import
> yo'nalishlari, asosiy oqimlar va tashqi tizimlar. Yangi dasturchi uchun
> boshlang'ich nuqta; to'liq reja esa `docs/PLAN.md`da.

## Texnologiyalar

- Python 3.11 + **Django 5.2 LTS** + **DRF** (REST) + **Channels** (WebSocket)
- PostgreSQL 16 (**PostGIS** — salon joylashuvi) + Redis (kesh, Celery broker, WS channel layer)
- Celery (worker + beat) — kunlik eslatmalar
- Auth: telefon + OTP (SMS) → **JWT** (access 15 min / refresh 7 kun, rotation + blacklist)
- Prod server: **gunicorn** + `uvicorn` ASGI worker'lari; statik — **whitenoise**

## Qatlamli tuzilma

```
backend/
├── config/                  # sozlamalar (base/dev/test/prod), urls, asgi, celery, api_router
└── apps/
    ├── core/                # Region/District, health, audit log, swagger, umumiy fabrikalar
    ├── accounts/            # User (telefon=login), OTP, JWT, audit
    ├── salons/              # Salon (PostGIS Point), moderatsiya holatlari
    ├── barbers/             # BarberProfile, kabinet service'lari (tanaffus, dam olish)
    ├── services/            # Service, ServiceCategory (barber yoki salon egaligida)
    ├── schedule/            # WorkSchedule, ScheduleBreak, DayOff + slot dvigateli
    ├── bookings/            # Appointment, AppointmentHistory, state machine, katalog API
    ├── notifications/       # Notification (DB) + WS push + signallar
    ├── reviews/             # Review (1:1 appointment), barber reytingi
    ├── analytics/           # hisobotlar (bookings faqat o'qiydi) + Excel eksport
    ├── telegram/            # chat bog'lash, webhook, eslatma ko'prigi
    └── web/                 # SSR/UI — faqat taqdimot: boshqa app'lardan import YO'Q
```

Har app ichida: `models.py`, `api/` (view + serializer — **logika YO'Q**),
`services/` (**biznes mantiq faqat shu yerda**), `tests/`, `factories.py`.

## Import yo'nalishlari (qat'iy qoida)

```
core ← accounts ← salons/barbers ← services/schedule ← bookings ← notifications/reviews
analytics ← bookings (faqat o'qiydi)
telegram ← notifications.emitter + accounts (chat bog'lash)
```

1. Importlar faqat **yuqoriga**: `bookings → schedule` OK; teskarisi ❌
2. Biznes logika faqat `services/`da; view/bot handler faqat chaqiradi
3. Tashqi tizimlar (SMS, Telegram) **adapter orqali** — `Console*` (dev) /
   real provayder (prod), muhit o'zgaruvchisi bilan tanlanadi
4. `apps.web` (UI) boshqa app'lardan import qilmaydi — ma'lumot faqat
   `/api/v1/*` (JWT `localStorage`da) va WS orqali

## Asosiy oqimlar

### Navbat olish (asosiy biznes)
1. Mijoz katalogda sartarosh tanlaydi → `GET /catalog/barbers/{id}/slots/?service_id=&day=`
   — slot dvigateli jadval + tanaffus + dam olish + band soatlar + xizmat
   davomiyligini hisoblab bo'sh oraliqlarni qaytaradi (boshqa servisga bog'liq emas)
2. `POST /bookings/` — slot yana tekshiriladi; `UNIQUE (barber, date, start_time)
   WHERE status NOT IN (CANCELLED, REJECTED)` bazaviy race-himoya
3. Holat mashinasi: `PENDING → CONFIRMED → COMPLETED`
   (yoki `REJECTED` / `CANCELLED` / `NO_SHOW`) — `services/state_machine.py`
   barcha o'tishlarni tekshiradi, har o'tish `AppointmentHistory`ga yoziladi
4. Har o'zgarish signal orqali: DB xabarnoma → WS push (jonli UI) →
   Telegram (chat bog'langan bo'lsa) → SMS fallback (chat yo'q bo'lsa)

### Auth oqimi
`register/login` (telefon) → SMS kod (OTP, 5 xonali, 3 urinish limit) →
`verify-otp` → access+refresh → `refresh` (rotation, eskisi blacklist) → `logout`.

### Telegram zanjiri (bosqich 7)
Kabinet `POST /telegram/link/` (6 xonali kod, 15 daqiqa) → foydalanuvchi
botga `/start KOD` → webhook chatni bog'laydi → barcha navbat xabarlari
Telegram'ga, eslatmalar `send_reminders` (Celery beat, har kuni 09:00).

## Kesh va WS

- Redis 3 DB: `0` kesh, `1` Celery broker, `2` WS channel layer
- WS: `/ws/client/{user_id}/` va `/ws/barber/{user_id}/` — JWT `?token=`
  bilan auth (brauzer header yubora olmaydi); noto'g'ri token → ulanish rad

## Prod arxitektura (bosqich 9)

```
[TLS proxy (nginx/caddy)] → [gunicorn + 4×uvicorn worker (web)]
     │                                │
     │                          [celery worker] [celery beat]
     └── whitenoise: statik → media: Django serve (yuk ortsa nginx'ga)
                                   │
                      PostgreSQL 16 (pgdata volume) + Redis
```

Batafsil deploy va operatsiyalar: `docs/DEPLOY.md`.

## Testlar

- 456 test, coverage 99% (gate ≥80%); markerlar: `unit`, `integration`, `e2e`
- E2E oqimlar: `apps/core/tests/test_e2e_flows.py`; IDOR suite:
  `apps/core/tests/test_idor.py` (49 test — 404/403/400, sizib chiqish yo'q)
- Sozlamalar: `config/settings/test.py` — tez parol hash, locmem kesh,
  Celery eager, OTP kodlar `fake_sms` fixture orqali

## Konventsiyalar

- Til: kod izohlari va UI **o'zbekcha**; verbose_name'lar migration'larda
- Lint/format: **ruff** (pre-commit bilan), `ruff check && ruff format`
- Migration'lar: har model o'zgarishi alohida app migration'i
- API: `/api/v1/` prefiks; ro'yxatlar pagination bilan (`results`)
