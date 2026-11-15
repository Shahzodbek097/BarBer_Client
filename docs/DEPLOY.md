# BarBer_Client — Deploy va Operatsiya kitobchasi

> Production stack: `docker/docker-compose.prod.yml` (bosqich 9).
> Lokal dev ko'tarish uchun README "Tez boshlash" bo'limiga qarang.

## Talablar

- Docker + Docker Compose v2 (Linux yoki Docker Desktop)
- Domain + TLS reverse proxy (nginx yoki caddy) — prod'da HTTPS shart
- 2 GB+ RAM, 2+ CPU

## Muhit o'zgaruvchilari

Majburiylar compose `${VAR:?}` bilan tekshiriladi — bo'lmasa stack
umuman ko'tarilmaydi:

| O'zgaruvchi | Majburiy | Tafsilot |
|---|---|---|
| `SECRET_KEY` | ✅ | 50+ tasodifiy belgi (Django imzo kaliti). Generatsiya: `-join ((1..64) \| %{ '{0:x}' -f (Get-Random -Max 16) })` |
| `POSTGRES_PASSWORD` | ✅ | Kuchli DB parol — **birinchi ko'tarishda** belgilanadi, keyin o'zgartirilmasin (bazadagi rol paroli o'zgarmaydi) |
| `ALLOWED_HOSTS` | ✅ | Ver avgul, `,` bilan: `<domain>,<ip>` |
| `WEB_PORT` | — | Host port (default 8000) |
| `SECURE_SSL_REDIRECT` | — | Default `1` (HTTPS'ga redirect). TLS'siz lokal drill'da `0` |
| `SMS_PROVIDER` | — | `console` (default, SMS logga yoziladi) yoki `eskiz` |
| `SMS_ESKIZ_EMAIL` / `SMS_ESKIZ_PASSWORD` | — | Eskiz provayder kredensiallari |
| `TELEGRAM_BOT_TOKEN` | — | Bot tokeni (bo'sh → eslatmalar SMS fallback'ga) |
| `TELEGRAM_WEBHOOK_SECRET` | — | Webhook URL maxfiy qismi |

> **Sirlar image'ga kirmaydi** — `.dockerignore` `.env`ni chiqaradi;
> compose env orqali beriladi (CI/CD secret'larida saqlang).

## Birinchi deploy

```bash
# 1) Kod + .env (yoki CI secret'lar)
git clone <repo> && cd BarBer_Client

# 2) Majburiy env'lar bilan ko'tarish (migratsiya + regions avtomatik)
export SECRET_KEY=... POSTGRES_PASSWORD=... ALLOWED_HOSTS=...
docker compose -f docker/docker-compose.prod.yml up -d --build

# 3) Tekshirish
curl http://<domain>/health/            # {"status": "ok"}
curl http://<domain>/api/v1/catalog/regions/ | head
python scripts/rollback.py --record     # deploy SHA'ni yozib qo'yish
```

Web konteyner startda `migrate --noinput && loaddata regions && gunicorn`
bajaradi (gunicorn `exec` orqali — signal'lar to'g'ri yetadi).

## TLS proxy (misol: nginx)

```nginx
server {
    listen 443 ssl http2;
    server_name barber.uz;
    # ssl_certificate ...;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto https;      # SECURE_PROXY_SSL_HEADER
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;        # WebSocket
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 300s;
    }
}
```

## Zaxiralash

```bash
python scripts/backup_db.py                     # pg_dump -Fc → backups/*.dump (14 ta saqlanadi)
python scripts/backup_db.py --container barber_prod_db   # default shu
```

Cron (har kuni 02:30, Linux host):

```cron
30 2 * * * cd /srv/BarBer_Client && /usr/bin/python3 scripts/backup_db.py >> backups/backup.log 2>&1
```

Zaxira fayllari **offsite'ga** ko'chirilishi shart (rsync/S3) — bitta
hostdagi zaxira haqiqiy zaxira emas.

## Tiklash (restore)

```bash
# Drill — har oy tekshirish tavsiya etiladi:
python scripts/restore_drill.py --latest        # scratch DB'ga tiklab, 32 jadvalni solishtiradi

# Haqiqiy tiklash (bazani almashtirish):
docker exec barber_prod_db psql -U barber -d postgres -c "DROP DATABASE IF EXISTS barber_client;"
docker cp backups/<fayl>.dump barber_prod_db:/tmp/restore.dump
docker exec barber_prod_db pg_restore -U barber -d postgres -C --no-owner /tmp/restore.dump
docker compose -f docker/docker-compose.prod.yml restart web worker beat
```

## Rollback (kod yoki DB)

```bash
# Deploy paytida (bir marta): joriy SHA yoziladi
python scripts/rollback.py --record

# Muammo bo'lsa — oldingi deploy'ga qaytish (checkout → rebuild → health)
python scripts/rollback.py --to last_deploy
python scripts/rollback.py --to HEAD~1

# DB migratsiyasini ham orqaga surish (ma'lumot yo'qolishi mumkin — avval backup!)
python scripts/backup_db.py
python scripts/rollback.py --to last_deploy --db-rollback bookings 0001
```

Script build muvaffaqiyatsiz bo'lsa avtomatik oldingi holatga qaytaradi.

## Kuzatish (monitoring)

- Health: `GET /health/` → 200 `{"status": "ok"}` (compose healthcheck ham shu)
- Loglar: `docker logs barber_prod_web` + prod'da aylanadigan fayl
  `backend/logs/barber.log` (5 MB × 5)
- Celery: `docker logs barber_prod_worker`, beat jadvali — kunlik 09:00 eslatma
- Yuk: `python scripts/load_test.py --url https://<domain> --users 20 --requests 240`
  — gate: p95 < 500 ms (bosqich 8'da 242 ms o'lchangan)

## Yangilanish tartibi

```bash
git pull
docker compose -f docker/docker-compose.prod.yml up -d --build   # migrate startda
curl -f http://<domain>/health/ || echo "MUAMMO — rollback"
python scripts/rollback.py --record                              # muvaffaqiyatli deploy yozuvi
```
