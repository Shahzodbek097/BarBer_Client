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

### Bosqich 3 — Foydalanuvchilar va autentifikatsiya ✅
- Telefon + OTP autentifikatsiya: 5 xonali kod, bazada faqat sha256 hash
  (`hmac.compare_digest` bilan solishtirish)
- OTP himoyasi: 3 xato urinish limiti, 60s qayta yuborish dami, bir telefon soatiga
  5 kod limiti, kod umri 5 daqiqa — `OTP_CONFIG` orqali sozlanadi
- SMS adapterlar (plan qoidasi: tashqi tizim adapter orqali): `console` (dev, logga
  yozadi) va `eskiz` (prod, `notify.eskiz.uz`; token keshlanadi) — provayder
  `SMS_PROVIDER=.env` dan tanlanadi
- JWT: access 15 min / refresh 7 kun, `ROTATE_REFRESH_TOKENS` +
  `BLACKLIST_AFTER_ROTATION` (token_blacklist app); logout refresh'ni blacklist'ga
  tushiradi, chet token uchun 403
- API (`/api/v1/auth/`): `register` (client/barber/salon_admin; superadmin rad
  etiladi), `login`, `verify-otp`, `refresh` (o'chirilgan user → 401, bloklangan →
  403), `logout`, `me` (GET/PATCH: full_name, lang, avatar)
- Service qatlami: `core/services/audit.py` (hech qachon buzilmaydigan audit),
  `accounts/services/{exceptions,sms,otp,auth}.py` — viewlar faqat chaqiradi
  (logika yo'q qoidasi)
- Rollar: `IsNotBlocked` default guard + `IsClient/IsBarber/IsSalonAdmin/IsSuperAdmin/IsStaffRole`
  izolyatsiya matritsasi testlari (4 rol × 4 klass)
- Throttling (DRF ScopedRateThrottle): register 5/min, otp (login) 5/min, otp_verify 10/min
- `debug_code` javobda faqat `DEBUG=True` **va** `SMS_PROVIDER=console` bo'lgandagina
  qaytadi
- Audit jurnalida: `user_registered`, `otp_verified_{purpose}`
- Natija: **137 test yashil** (oldingi 83 + 54 yangi: auth API oqimi, OTP servis,
  SMS adapter, rol matritsasi, throttling), coverage **99%** (auth ≥85% gate bajarildi);
  live smoke Docker'da tekshirildi: register → verify-otp → me → logout to'liq oqim OK

### Bosqich 4 — Asosiy biznes mantiq (domen) ✅
- **Slot dvigateli** (`schedule/services/slots.py`): sof funksiya
  `compute_day_slots` — plan qoidasiga ko'ra dvigatel `bookings`'ni bilmaydi,
  band vaqtlar `(start, end)` juftliklari argument sifatida kiradi. Yarim ochiq
  oraliq mantig'i `[start, end)` ("aynan tegish" kesishmaydi), 15 daqiqalik
  panjara, tanaffus/band/o'tgan-vaqt filtrlari, moslashtiriladigan qadam
- DB yordamchilari: `day_work_interval` (DayOff > is_working > jadval),
  `day_breaks`, `available_slots` (jadval + tanaffus + band integratsiyasi)
- **Holat mashinasi** (`bookings/services/state_machine.py`): yagona
  `TRANSITIONS` matritsasi (PENDING→CONFIRMED/REJECTED/CANCELLED;
  CONFIRMED→COMPLETED/NO_SHOW/CANCELLED; qolganlari terminal),
  `transition()` — validatsiya + saqlash + `AppointmentHistory` + audit atomik
- **Booking servis** (`bookings/services/appointments.py`): `create_appointment`
  (barber/xizmat/sana validatsiyalari, slot dvigateli tekshiruvi, narx va
  vaqt muzlatish, `IntegrityError → SlotUnavailable 409`),
  `confirm/reject/cancel/complete/mark_no_show/propose_new_time` — har amalda
  egalik tekshiruvi (sartarosh yoki ishtirokchi), `propose_new_time` navbatni
  yangi bo'sh slotga ko'chiradi va holatni PENDING'da qoldiradi
- Xatolar (`bookings/services/exceptions.py`): BookingValidationError 400,
  AppointmentNotOwner 403, SlotUnavailable/InvalidTransition 409
- **Race-test**: 10 thread bir slotga bir vaqtda → **1 g'alaba, 9
  SlotUnavailable** — `appointment_active_slot_unique` partial unique index
  orqali (real Postgres, `django_db(transaction=True)`)
- Natija: **224 test yashil** (87 yangi: dvigatel matritsasi, DB integratsiya,
  state machine, yaratish validatsiyalari, amallar, race), domen coverage
  **99–100%** (`slots.py` 100%, `state_machine.py` 100%, `appointments.py` 99%)
  — gate ≥90% bajarildi; jonli smoke Docker'da: 9–18 kunlik jadvalda 35 slot,
  create→confirm→complete (tarix 3 yozuv), band slotga qayta urinish
  `SlotUnavailable` bilan rad etildi

### Bosqich 5 — API va backend (REST + WebSocket) ✅
- **Swagger/OpenAPI** (`drf-spectacular`): `/api/schema/` (sxema) va
  `/api/docs/` (Swagger UI). Gate: barcha majburiy endpointlar sxemada bor
  (`test_swagger.py` ro'yxat bilan tekshiradi — auth, katalog, bookings,
  kabinetlar, reviews, notifications, admin)
- **Katalog API** (`/api/v1/catalog/*`, ochiq/AllowAny): regions
  (+`/districts/`), salons (faqat APPROVED, filtrlar region/district/search),
  barbers (APPROVED, filtrlar salon/search/is_active) + `services/` (o'ziniki
  va saloni xizmatlari) + `slots/` (slot dvigateli + band navbatlar;
  `service_id`/`day` validatsiya, boshqa sartarosh xizmati → 400)
- **Navbat API** (`/api/v1/bookings/*`): mijoz — `create` (slot band bo'lsa
  409, nofaol sartarosh → 400), `my` (?status=), `retrieve/cancel/reschedule`
  (faqat ishtirokchi — qo'shimcha Q-filtr + service egalik tekshiruvi, notanish
  → 404); sartarosh — `incoming` (?status=&day=), `manual` (orxonadagi mijoz,
  telefon bo'yicha), `confirm/reject/propose/complete/no-show`; mijozning
  sartarosh amallariga urinishi → 403. View'lar faqat services chaqiradi
  (logika yo'q qoidasi)
- **Sartarosh kabineti** (`/api/v1/barber/*`): profile (GET/POST onboarding/
  PATCH), services CRUD (o'chirish = soft `is_active=False` — navbatlar
  PROTECT), haftalik jadval GET/PUT (update_or_create — tanaffuslar saqlanadi),
  tanaffuslar (ish vaqti ichida bo'lishi shart), dam olish kunlari,
  Faol/Nofaol tugmasi. Barchasi `IsBarber`, izolyatsiya ikki qatlamli
- **Salon egasi** (`/api/v1/salon/*`): profil GET/PATCH (status/joylashuv
  tahrirlanmaydi — moderatsiya), o'z salonidagi sartaroshlar ro'yxati
- **Sharhlar** (`/api/v1/reviews/`): yaratish faqat COMPLETED navbatga,
  har navbat 1 sharh, yaratilganda sartarosh `rating_avg/rating_count`
  qayta hisoblanadi; ochiq ro'yxat `/reviews/barber/{id}/` (faqat ko'rinadiganlar)
- **Xabarnomalar** (`/api/v1/notifications/*`): ro'yxat (faqat o'ziniki),
  `read`, `read-all`, `unread-count` (badge)
- **Super admin** (`/api/v1/admin/*`): salonlar ro'yxati (?status=),
  `approve`/`block` (audit bilan), umumiy statistika (`users/salons/
  appointments` bo'yicha hisoblar) — statistika `bookings/services/stats.py`da
  (import yo'nalishi buzilmaydi)
- **WebSocket push** (`channels` + `channels-redis`): `/ws/client/{user_id}/`
  va `/ws/barber/{user_id}/` — JWT `?token=` bilan (brauzer WS'da header
  yuborolmaydi), yaroqsiz/egasi mos kelmaydigan token → ulanish yopiladi.
  Hodisalar signal orqali (`notifications/signals.py`: `bookings` import
  yo'nalishini Buzmaslik uchun) — yangi navbat → sartarosh push, har holat
  o'tishi → qarama-qarshi tomonga push
- **Muhit**: `daphne` (ASGI) INSTALLED_APPS boshida, dev compose'da
  `REDIS_CHANNEL_URL` qo'shildi (redis 6379/2); testlarda InMemory layer
- Natija: **334 test yashil** (110 yangi: katalog, bookings, kabinet, salon,
  reviews, notifications, admin, Swagger gate, WS push — InMemory layer bilan),
  umumiy coverage **99%** (gate ≥80% bajarildi). Jonli smoke Docker'da:
  `/health/` OK, `/api/schema/` + `/api/docs/` 200, Redis channel layer
  round-trip OK, haqiqiy WS ulanish → yangi navbat yaratilganda push qabul
  qilindi (daphne + Redis layer)

### Bosqich 6 — Frontend va dizayn ✅
- **`apps/web`** — faqat taqdimot qatlami (presentational): boshqa app'lardan
  import YO'Q; barcha ma'lumot `/api/v1/*` orqali (JWT `localStorage`da), WS
  native `WebSocket ?token=` bilan. Build qutisi yo'q: Django template + vanila
  JS (ES module) + qo'l bilan yozilgan mobil-first CSS
- **Sahifalar va roliq izolyatsiyasi**: `/` ochiq katalog (region/search filtrlar,
  salon kartalari), `/salon/{id}/` salon sahifasi (sartaroshlar + xizmatlar),
  `/barber/{id}/` sartarosh sahifasi (xizmat tanlash → bo'sh slot → navbat);
  ro'yxatdan o'tmagan foydalanuvchi navbat olishga urinsa intent
  `sessionStorage (bb_pending_booking)`'ga saqlanadi → auth oqimi → `?next`
  qaytish → navbat avtomatik band qilinadi; kabinetlar: `/c/` (mijoz —
  holat tablari, vazncha, bekor qilish, vaqt o'zgartirish modali, sharh
  yozish), `/barber/` (onboarding, kiruvchi so'rovlar: tasdiqlash / rad etish
  javob modali bilan / yangi vaqt taklif (sana + slot panjara) / bajarildi /
  kelmadi / bekor qilish, qo'lda navbat yozish, Faol-Nofaol, haftalik jadval
  va xizmatlar sahifasi), `/salon/` (profil forma, sartaroshlar ro'yxati),
  `/panel/` (8 statistika kartasi, salon moderatsiyasi approve/block),
  `/notifications/` (ro'yxat, o'qilgan qilish, barchasini o'qish + badge)
- **Statik versiyalash**: `STATIC_VERSION` + context processor — barcha statik
  linklar `?v={{ STATIC_VERSION }}` (brauzer keshini buzish)
- **Dizayn tizimi**: CSS o'zgaruvchilar (brand/ink/line...), `.card/.btn/.tag/
  .chip/.modal/.toast/.stats` komponentlari; breakpoint'lar 768/1440
- **Responsive 360/768/1440**: katalog grid 1→2→3 ustun, statistika 2→4 ustun,
  filtrlar mobil-da ustunli → 768+ qatorli, topbar mobilda 2 qator (logo+user /
  menyular), 768+ bitta qator — computed style + skrinshot bilan tekshirildi
- **E2E (brauzer, dasturiy)**: US-1 anon → ro'yxatdan o'tish → avto-navbat
  to'liq oqim; US-2 ro'yxat/bekor qilish/vaqt o'zgartirish; US-3/US-4 sartarosh
  amallarining barchasi (modallar bilan); US-5 salon forma saqlash; US-6 panel
  statistika + salon tasdiqlash; US-7 sharh yozish (reyting yangilanadi);
  xabarlar read-all; **WS push jonli isbotlandi**: service-layer'dan navbat
  yaratilganda toast ("Yangi navbat so'rovi — ..."), `bb:notify` event va
  badge oshishi + ro'yxat avto-yangilanishi bir vaqtda kuzatildi
- E2E davomida topilgan va tuzatilgan: kabinet ota-konteynerlari `hidden`
  qolishi, `[hidden]` atributini CSS `display` yengib o'tishi (universal
  `[hidden]{display:none!important}` reset), read-all'dan keyin badge 0 ga
  tushmasligi
- **dev.py**: `X_FRAME_OPTIONS = "SAMEORIGIN"` (faqat dev — prod `DENY`)
- Natija: **364 test yashil** (20 sahifa smoke test: har page 200 + xatolar),
  coverage **99%**; gate — US-1…US-7 UI'da to'liq, responsive 3 ko'rsatgich,
  WS push ishlaydi — bajarildi

### Bosqich 7 — Hisobotlar, Telegram bot, eslatmalar ✅
- **`apps/analytics`** — hisobotlar (bookings FAQAT o'qiydi):
  `services/reports.py` (`barber_daily` — kunlik ro'yxat + holat kesimi +
  daromad, `salon_period` / `admin_period` — davriy, guruhlangan); daromad =
  bandlov paytida muzlatilgan `price`, faqat COMPLETED (bekor/rad qilinganlar
  pul emas); rol izolyatsiyasi: sartarosh o'zi, salon egasi o'z saloni,
  super admin hammasi
- **Excel eksport**: `services/xlsx.py` (openpyxl) + `XLSXRenderer` — DRF
  `?format=xlsx` muzokarasidan o'tkazadi (mos renderer bo'lmasa DRF Http404
  ko'taradi); `/api/v1/barber/report/`, `/api/v1/salon/report/`,
  `/api/v1/admin/report/` — JSON yoki xlsx (bo'sh ajratgich + "Jami" qatori)
- **`apps/telegram`** (yangi app): `TelegramChat` (user↔chat 1:1) va `LinkCode`
  (6 xonali, 15 daqiqa umr); oqim: kabinet POST `/api/v1/telegram/link/` →
  foydalanuvchi botga `/start KOD` → webhook chatni bog'laydi
- **Webhook**: `/telegram/webhook/<secret>/` — `X-Telegram-Bot-Api-Secret-Token`
  sarlavhasi bilan himoyalangan (bo'sh/mos kelmagan → 403); bot adapterlari:
  `ConsoleBot` (token bo'lmasa logga yozadi) / `HttpBot` (api.telegram.org)
- **Notification → Telegram ko'prik**: `TelegramConfig.ready()` ichida
  `post_save` signal (telegram → notifications import yo'nalishi qonuniy);
  SYSTEM turi tashlab yuboriladi; barcha navbat xabarlari bog'langan chatga
  ketadi, xato asosiy oqimni buzmaydi (faqat log)
- **Eslatmalar**: `send_reminders_for(day)` — tasdiqlangan va `reminded_at`
  bo'sh navbatlar; chat bor → Telegram (`notify()` ko'prigi orqali), chat
  yo'q → SMS fallback (`accounts/services/sms.py` adapteri); idempotentlik —
  `Appointment.reminded_at` (migratsiya `bookings.0002`); Celery Beat har kuni
  09:00 (`apps.telegram.send_reminders`, compose'da `worker --beat`) +
  `manage.py send_reminders` (qo'lda / dev)
- **UI**: mijoz kabinetida "Telegram eslatmalari" kartasi (holat + kod olish,
  `.code-line`), sartarosh/salon/panel kabinetlarida Excel eksport tugmalari
  (`api.js downloadFile` — JWT bilan blob yuklab olish, 401 refresh bilan)
- **E2E isboti (haqiqiy HTTP)**: kabinetdan kod olish (kod 163585) → webhook
  `/start KOD` → chat bog'landi ("✅ Ulashdi, Ali Mijoz!") → navbat tasdiqlash
  → Telegram'ga "💈 Navbat tasdiqlandi" ketdi → `send_reminders`: bog'langan
  Ali'ga Telegram eslatma, chat'siz Bekzod'ga SMS fallback (console log) →
  Excel hisobot HTTP orqali yuklab olindi (openpyxl bilan qatorlar tekshirildi)
- Natija: **404 test yashil**, coverage **99%** (telegram va analytics
  modullarida ~100%); gate — zanjir (navbat→tasdiq→eslatma), Excel eksport,
  SMS fallback — bajarildi

### Bosqich 8 — Test va xavfsizlik ✅
- **IDOR testlar to'plami** (`apps/core/tests/test_idor.py`, 49 test):
  navbat obyekt izolyatsiyasi (retrieve/cancel/reschedule/list — boshqa
  mijozning navbati 404 va o'zgarmas), sartarosh amal izolyatsiyasi
  (confirm/reject/propose/complete/no-show/cancel — boshqa sartarosh 404,
  holat va taklif yozuvi o'zgarmas), xabarnoma izolyatsiyasi (detail/read/
  list/unread-count), sartarosh kabineti (xizmat PATCH/DELETE, tanaffus,
  dam olish kuni — 400 va o'zgarmas), salon izolyatsiyasi, admin 403
  matritsasi (3 rol × 3+ endpoint), Telegram holat izolyatsiyasi,
  12 endpoint autentifikatsiyasiz 401 — javoblar 404/403/400, hech qachon
  boshqa obyekt haqida ma'lumot sizib chiqmaydi
- **E2E 3 oqim** (`apps/core/tests/test_e2e_flows.py`, `e2e` marker):
  US-1 anon katalog → ro'yxatdan o'tish (OTP) → navbat → sartarosh tasdiqlaydi
  → mijoz holat + xabarnoma ko'radi; US-2 vaqt o'zgartirish → sartarosh taklifi
  → bekor qilish (tarix ≥ 3); US-3 qo'lda yozish → tasdiq → bajarildi →
  5 yulduzli sharh → kunlik hisobot daromadi 50 000 + katalogda reyting
- **Yuk testi** (`scripts/load_test.py` — stdlib+requests, ThreadPoolExecutor):
  8 endpoint (health, sahifalar, katalog API) × 20 parallel × 240 so'rov,
  har endpoint uchun ort/p50/p95/p99, gate p95<500 ms; natija:
  `runserver` (1 jarayon) p95 **516 ms** — qat'iy o'tmadi; dev compose
  prod-shakliga o'tkazildi: `gunicorn config.asgi:application -k
  uvicorn.workers.UvicornWorker -w 4` (WS saqlanadi — ASGI) → p95 **242 ms**
  (throughput 53 → 154 req/s), xatolar 0 — gate bajarildi. Dastlabki
  p95 44 ms (1 foydalanuvchi) — bottleneck server jarayonlari sonida edi,
  ilova kodida emas (katalogda select_related/prefetch_related bor)
- **pip-audit**: `requirements/base.txt` (kutubxonalar versiyalari bilan)
  tekshirildi — **0 ma'lum zaiflik**; `gunicorn>=23`, `uvicorn[standard]>=0.30`
  qo'shildi (asosiy talablar — prod'da ham kerak)
- **WS smoke**: yangi serverda haqiqiy JWT bilan handshake OK
  (`/ws/client/{id}/`), noto'g'ri token 403 rad etiladi (consumer
  xatti-harakati to'g'ri)
- Natija: **456 test yashil**, coverage **99%** (66/5170 qator), ruff toza,
  yuk p95 242 ms, pip-audit 0 — gate: coverage ≥80% ✅, E2E 3 oqim ✅,
  IDOR suite ✅, p95<500ms ✅, pip-audit toza ✅
