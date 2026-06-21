# ContentFlow — Deployment Runbook (cheap VPS)

Target: a single ~$5–6/mo VPS (Hetzner CX22 / DigitalOcean basic). One `docker compose up`.
The full stack (Postgres, Redis, MinIO, Qdrant, FastAPI, 3 Celery workers, beat, Next.js web,
nginx) runs from the committed [docker-compose.yml](../docker-compose.yml).

> Free tiers (Render/Railway) spin workers down and drop scheduled posts — that's why we use a
> small always-on VPS. Frontend can optionally move to Vercel free later.

## 0. Prerequisites
- A VPS (Ubuntu 22.04+), 2 GB RAM min (4 GB comfortable with Qdrant + workers).
- A domain pointed at the VPS IP (A record). HTTPS needs a hostname.
- Docker + Docker Compose v2 installed on the VPS.

## 1. Clone + branch
```bash
git clone <repo> contentflow && cd contentflow
git checkout real-implementation-main
```

## 2. Secrets (never commit these)
Both env files are gitignored. Create them on the VPS:

**Root `.env`** (compose infra creds) — copy `.env.docker.example`, then set STRONG values:
```bash
cp .env.docker.example .env
# set: POSTGRES_PASSWORD, MINIO_ROOT_PASSWORD, GF_ADMIN_PASSWORD  (openssl rand -base64 24)
```

**`backend/.env`** — copy `backend/.env.example`, then generate the required secrets:
```bash
cp backend/.env.example backend/.env
python -c "import secrets; print('APP_SECRET_KEY='+secrets.token_hex(64))"
python -c "import secrets; print('JWT_SECRET_KEY='+secrets.token_hex(64))"
python -c "from cryptography.fernet import Fernet; print('TOKEN_ENCRYPTION_KEY='+Fernet.generate_key().decode())"
```
Set `APP_ENV=production` and a real `APP_ALLOWED_ORIGINS` (your https domain). The app **refuses to
boot in production** with weak/missing `APP_SECRET_KEY`/`JWT_SECRET_KEY`/`TOKEN_ENCRYPTION_KEY`.

Platform/API creds (fill as you obtain them — app runs without them, those platforms just show
"not configured"): `GEMINI_API_KEY` (free, primary LLM), `LINKEDIN_CLIENT_ID/SECRET`,
`GOOGLE_*`/`YOUTUBE_*`, later `INSTAGRAM_*`/`FACEBOOK_*`/`TWITTER_*`.

> **Rotate** the dev keys currently in your local `backend/.env` before reusing anywhere — treat
> them as compromised if they were ever shared.

## 3. Bring it up
```bash
docker compose up -d --build           # builds backend + web, runs `alembic upgrade head`, starts all
docker compose ps                      # all healthy?
docker compose logs -f backend         # watch migration + boot
curl -s http://localhost:8000/health   # {"status":"ok",...}
```

## 4. HTTPS (recommended: Caddy in front)
`nginx` in compose serves HTTP on the host. Simplest TLS is a Caddy reverse proxy (auto Let's Encrypt):
```
# /etc/caddy/Caddyfile
your-domain.com {
    reverse_proxy localhost:80      # nginx (web + /api → backend)
}
```
Then set `backend/.env` `APP_ALLOWED_ORIGINS=https://your-domain.com` and the web build arg
`NEXT_PUBLIC_API_URL`/`BACKEND_URL` accordingly, and rebuild the frontend.

Networking hardening: only expose 80/443 publicly; keep db/redis/minio/qdrant on the compose
network (do not publish their ports on the public interface).

## 5. Postgres backups (nightly)
```bash
# /etc/cron.daily/contentflow-db-backup  (chmod +x)
#!/bin/sh
docker compose -f /path/contentflow/docker-compose.yml exec -T db \
  pg_dump -U postgres social-media-distribution | gzip > /var/backups/cf-$(date +%F).sql.gz
find /var/backups -name 'cf-*.sql.gz' -mtime +14 -delete
```

## 6. Smoke test (prod)
```bash
# register -> login -> connect (Mastodon/Bluesky paste creds) -> create -> schedule -> publish
# scheduled posts fire via celery beat (process_publish_jobs every 5 min)
```

## 7. Platform go-live checklist
- **Mastodon / Bluesky**: work immediately (paste creds in Settings → Accounts). Best for first live demo.
- **LinkedIn**: dev app + `w_member_social`; connect via redirect OAuth.
- **YouTube**: Google Cloud OAuth client; own channel, test mode.
- **Pinterest**: trial = sandbox until 2nd review.
- **Instagram/Facebook**: start Meta App Review + business verification early (weeks).
- **X/Twitter**: pay-per-post; keep behind a flag.

## Cost
Recurring: VPS ~$5–6/mo. One-time: Google Play $25 (when shipping the Android wrap). Free:
Gemini tier, Mastodon/Bluesky/LinkedIn/YouTube dev, MinIO/Redis/Qdrant self-hosted.
