# Phase 0 Baseline — "What Actually Works"

_Branch: `real-implementation-main` · Established: 2026-06-21 · Stack brought up via Docker Compose on Windows + Docker Desktop._

This is the verified ground-truth baseline before any feature work. Every claim below was confirmed by booting the stack and exercising it — not inferred from code.

## How to run (local)

```bash
docker compose up -d backend          # starts db, redis, minio, qdrant + backend (runs alembic migrations then uvicorn)
curl http://localhost:8000/health     # {"status":"ok","version":"2.0.0","env":"development"}

# Tests (run inside the backend container; test DB auto-derives to <db>_test and auto-creates):
docker compose exec -T backend pytest -q
```

Notes:
- **Windows can't run the backend natively** — it uses `uvloop`/`httptools` (no Windows wheels). Docker is the only run path on this machine.
- `backend/.env` `DATABASE_URL` uses `localhost`; Compose overrides it to `db:5432` for containers (YAML anchor). The localhost value only matters if running on the host.

## Verified WORKING (live, end-to-end)

| Area | Evidence |
|------|----------|
| Boot + migrations | `/health` 200; `alembic_version = 0001_baseline`; 41 tables in `public` |
| Register | `POST /api/v1/auth/register` → 201 |
| Password policy | Weak password correctly rejected (422, requires upper/lower/digit/special) |
| Login | `POST /api/v1/auth/login` → 200; sets HttpOnly `cf_access_token` (1h) + `cf_refresh_token` (30d, scoped to `/api/v1/auth`) |
| Session | `GET /api/v1/auth/me` via cookie → user + access token; workspace auto-bootstrapped |
| Platform list | `GET /api/v1/oauth/platforms` → instagram, youtube, tiktok, … with scopes/capabilities |
| Accounts list | `GET /api/v1/social-accounts` → `{"accounts":[],"total":0}` |
| Token vault | Fernet envelope encryption, per-workspace derived key, KEK from `TOKEN_ENCRYPTION_KEY` (verified present + valid) |

## Test suite

- **466 passed / 11 failed / 18 skipped** on first run.
- Fixed in Phase 0:
  - `tests/test_auth_service.py` — 4 login tests failed with `TypeError: '>=' not supported (AsyncMock vs int)`. **Test bug, not code bug**: the mocked cache never set `get_login_failures`'s return; production returns an int (verified `cache_service.py:95`). Fixed `_make_service` to return `0`.
  - `tests/conftest.py` — test-DB isolation bug: `DATABASE_URL.replace("/contentflow", "/contentflow_test")` was a **no-op** (real DB is `social-media-distribution`), so the suite ran against — and `DROP TABLE CASCADE`-ed — the **live dev DB**. Replaced with `_test_database_url()` (suffix `_test`, honors `TEST_DATABASE_URL`) + `_ensure_database_exists()` (idempotent auto-create).
- **Remaining 7 failures are environmental and on the cut list**: `test_competitor_intelligence.py` (6) + `test_trend_detection.py` (1) all fail with Playwright "chromium not installed". These test the **competitor/scraper** feature being removed in Phase 1 — their test files are deleted with the feature, not fixed.

## Gaps / bugs found (to fix in later phases)

| # | Severity | Finding | Fix in |
|---|----------|---------|--------|
| 1 | **HIGH** | OAuth connect registry `oauth_services` (oauth.py:37) only has **instagram, youtube, tiktok, twitter**. **LinkedIn, Facebook, Pinterest are NOT wired** despite having OAuth service files + publish adapters. LinkedIn (priority, creds in `.env`) is currently **unconnectable**. | Phase 2 |
| 2 | LOW | `GET /oauth/twitter/authorize` returns a 307 redirect even with empty Twitter creds (no config-present guard). | Phase 2/4 |
| 3 | INFO | Adapters exist for 7 platforms; **Mastodon, Bluesky, Threads not built** — the easy free platforms the strategy wants. | Phase 2 |

## Security notes

- Secrets are correctly **gitignored** — only `*.env.example` files are tracked. No committed secrets (verified `git ls-files`).
- `backend/.env` holds **live** keys (OpenAI, Gemini, Google OAuth secret, LinkedIn secret). **Rotate any that were ever shared/screenshotted/committed historically.**
- Configured platform creds today: **LinkedIn** + **Google/YouTube** (Google login) + **Gemini** + **OpenAI**. Empty: Instagram, Facebook, Twitter, VAPID.

## Bottom line

The backend is **real, not a Potemkin village**: it boots, migrates, authenticates, and exposes a coherent API. The core auth + token-vault + publish-pipeline foundation is solid. The main functional gap is OAuth connect wiring (3 built platforms unregistered) and the missing free-platform adapters — both addressed in Phase 2. Phase 1 removes the dead weight that's currently inflating the surface and failing tests.
