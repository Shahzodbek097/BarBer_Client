# BarBer_Client — Bosqichli Amalga Oshirish Rejasi

> Bu hujjat tasdiqlangan rejaning qisqartirilgan ko'rinishi. Bosqich yakunlangani
> sari shu fayl yangilanadi (natijalar bo'limi).

## 1. Bosqichlar va gate shartlari

| # | Bosqich | Muddat | Gate (o'tish sharti) |
|---|---------|--------|----------------------|
| 1 | Loyiha karkasi va konfiguratsiya | 3–4 kun | `compose up` → server ishlaydi; `pytest` yashil; settings `.env` dan o'qiydi |
| 2 | Ma'lumotlar bazasi va modellar | 4–5 kun | 17 jadval migratsiyasi; unique constraint testi; models coverage ≥80% |
| 3 | Foydalanuvchilar va autentifikatsiya | 1 hafta | OTP→JWT oqimi; 4 rol izolyatsiya matritsasi; auth coverage ≥85% |
| 4 | Asosiy biznes mantiq (domen) | 1,5 hafta | Slot dvigateli matritsasi; state machine; race-test (10 thread → 1 g'alaba); domen coverage ≥90% |
| 5 | API va backend | 1,5–2 hafta | Swagger'da barcha endpointlar; ruxsat matritsasi; API coverage ≥80%; view'da logika yo'q |
| 6 | Frontend va dizayn | 2 hafta | US-1…US-7 UI'da to'liq; responsive 360/768/1440; WS push ishlaydi |
| 7 | Hisobotlar va qo'shimchalar | 1 hafta | Telegram zanjiri (navbat→tasdiq→eslatma); Excel eksport; SMS fallback |
| 8 | Test va xavfsizlik | 1 hafta | Coverage ≥80%; E2E 3 oqim; IDOR suite; load p95<500ms; pip-audit toza |
| 9 | Docker va deploy | 4–5 kun | Prod URL ishlaydi; backup→restore drill; rollback skripti |
| 10 | Hujjatlashtirish | 3–4 kun | "Yangi dasturchi testi" (30 daqiqada local ko'tarish) |

## 2. Rollar

- **MIJOZ** — navbat oladi, o'z navbatlarini boshqaradi, sharh yozadi
- **SARTAROSH** — profil/xizmatlar/jadval; navbatni qabul/rad/taklif; faol-nofaol; kunlik tahlil
- **SALON EGASI** — salon profili, o'z sartaroshlarini boshqaradi, umumiy tahlil
- **SUPER ADMIN** — moderatsiya (PENDING→APPROVED/BLOCKED), umumiy statistika

Izolyatsiya: har rol alohida UI (`/c/`, `/barber/`, `/salon/`); umumiy bo'lgan yagona
narsa — ochiq katalog.

## 3. Modullar va bog'liqlik qoidalari

```
core ← accounts ← salons/barbers ← services/schedule ← bookings ← notifications/reviews
analytics ← bookings (faqat o'qiydi)
telegram ← notifications.emitter + accounts (chat bog'lash)
```

1. Importlar faqat yuqoriga: `bookings → schedule` OK; teskarisi ❌
2. Biznes logika faqat `services/` da; view va bot handler faqat chaqiradi
3. Tashqi tizimlar (SMS, Telegram) adapter orqali
4. Slot dvigateli `bookings`'ni bilmaydi — band vaqt ro'yxati argument sifatida

## 4. Ma'lumotlar bazasi (asosiy jadvallar)

`users` (role: CLIENT/BARBER/SALON_ADMIN/SUPERADMIN, phone unique) • `regions` •
`districts` • `salons` (Point, status: PENDING/APPROVED/BLOCKED) • `barbers`
(1:1 user, salon FK nullable, is_active_now, rating) • `service_categories` •
`services` (owner_type BARBER/SALON, duration_min, price Decimal) •
`work_schedules` • `schedule_breaks` • `day_offs` • `appointments`
(status: PENDING/CONFIRMED/COMPLETED/REJECTED/CANCELLED/NO_SHOW) •
`appointment_history` • `notifications` • `reviews` (1:1 appointment) •
`favorites` • `otp_codes` • `audit_logs`

Kritik constraint: `UNIQUE (barber, date, start_time) WHERE status NOT IN
(CANCELLED, REJECTED)` — ikkilangan bandlovdan bazaviy himoya.

## 5. API (v1) asosiy guruhlar

`/api/v1/auth/*` (register client/barber/salon, verify-otp, login, refresh, logout, me)
`/api/v1/catalog/*` (regions, salons, barbers + filtrlar, slots)
`/api/v1/bookings/*` (mijoz: create/my/reschedule/cancel; sartarosh: incoming/confirm/reject/propose/complete/no-show/manual)
`/api/v1/barber/*` (profile, services, schedule, day-offs, status/toggle, analytics)
`/api/v1/salon/*`, `/api/v1/notifications/*`, `/api/v1/reviews/*`, `/api/v1/admin/*`
WS: `/ws/barber/{id}/` (yangi so'rov push), `/ws/client/{id}/` (javob push)

## 6. Xavfsizlik

Telefon+OTP (Eskiz, 3 urinish limit) • JWT: access 15 min / refresh 7 kun + rotation+blacklist •
Role/object-level permission'lar • QuerySet izolyatsiyasi (IDOR oldini olish) •
Throttling (login 5/min) • HTTPS/HSTS/CORS • Audit log • O'zR shaxsiy ma'lumotlar qonuniga muvofiqlik

## 7. Yakunlangan bosqichlar natijasi

### Bosqich 1 — Loyiha karkasi va konfiguratsiya ✅
- Django 5.2 LTS skeleton, split-settings (base/dev/test/prod), `.env` orqali konfiguratsiya
- 10 app skeleti (api/services/migrations/tests strukturasi bilan)
- Docker dev compose: postgis/postgres16 + redis7 + web + celery (healthcheck bilan)
- pytest + pytest-django + factory-boy + ruff (lint+format) + pre-commit
- CI: lint + test (Postgres service bilan)
- `/health/` endpoint; logging sozlamalari
- Natija: gate shartlari bajarildi (README'dagi buyruqlar bilan tekshiriladi)

### Bosqich 2 — Ma'lumotlar bazasi va modellar ✅
- Kastom `User` (`AbstractUser`, telefon login, 4 rol: client/barber/salon_admin/superadmin,
  `is_verified`/`is_blocked`/lang) + `OTPCode` (sha256 hash)
- 17 biznes jadval + 1 M2M (specialties): `accounts_user`, `accounts_otpcode`, `core_region`,
  `core_district`, `core_auditlog`, `salons_salon`, `barbers_barberprofile`, `barbers_favorite`,
  `services_servicecategory`, `services_service`, `schedule_workschedule`, `schedule_schedulebreak`,
  `schedule_dayoff`, `bookings_appointment`, `bookings_appointmenthistory`,
  `notifications_notification`, `reviews_review` (+ `barbers_barberprofile_specialties`)
- 10 nomlangan constraint DB'da tasdiqlangan (9 `pg_constraint` + shartli UNIQUE
  `appointment_active_slot_unique` partial index sifatida)
- 9 app'da admin.py registratsiyalar (AuditLog faqat o'qish; BarBer jadval inline'lari schedule adminida)
- factory-boy factory'lar (9 app), regions fixture'i (14 viloyat / 53 tuman, pk: 1–14 / 101–153)
- Coverage `omit` (`admin.py`, `migrations/*`) — `pytest.ini`ga `--cov-config` orqali ulandi
- Natija: **83 test yashil** (79 model test), coverage **99%** (models ≥80% gate bajerildi);
  fresh `compose down -v && up` → migrate + `loaddata regions` avtomatik; `/admin/` 200
