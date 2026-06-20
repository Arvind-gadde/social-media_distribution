# ContentFlow Web — E2E Tests

Playwright-driven end-to-end, visual regression, and accessibility tests for
`apps/web`.

## Prerequisites

1. Install dependencies (from repo root):
   ```powershell
   pnpm install
   ```
2. Install the Chromium browser binary (one-time, per machine):
   ```powershell
   pnpm --filter @contentflow/web playwright:install
   ```
3. (Optional, for `@tier-3` auth tests) Backend running on
   `http://localhost:8000` with a seeded test user.

## Layout

```
tests/
  e2e/
    fixtures.ts      # `test`, `expect`, `authenticatedPage`, `axeScan()`
    smoke.spec.ts    # always-on smoke + visual baseline + a11y
    auth.spec.ts     # @tier-3 register/login/protected-route (scaffold only)
  visual/
    README.md        # snapshot workflow (see for details)
```

## Running tests

All commands assume CWD is the repo root.

| Goal | Command |
|------|---------|
| Run all E2E tests headless | `pnpm --filter @contentflow/web test:e2e` |
| Open Playwright UI mode | `pnpm --filter @contentflow/web test:e2e:ui` |
| Visual regression only | `pnpm --filter @contentflow/web test:visual` |
| Update visual baselines | `pnpm --filter @contentflow/web test:e2e -- --update-snapshots` |
| Run only smoke tests | `pnpm --filter @contentflow/web test:e2e -- --grep @smoke` |
| Enable tier-3 auth tests | `$env:RUN_TIER_3=1; pnpm --filter @contentflow/web test:e2e` |

The Playwright config starts `pnpm dev` automatically on port 3000 and reuses an
existing dev server if one is already running.

## Tags

- `@smoke` — must pass on every commit; the canary tier.
- `@visual` — pixel-diff tests; require committed baseline PNGs.
- `@tier-3` — deeper flows (auth, billing, settings). Skipped unless
  `RUN_TIER_3=1` is set, since they need a clean backend.

## Fixtures

```ts
import { test, expect, axeScan } from './fixtures';

test('dashboard a11y', async ({ authenticatedPage }) => {
  await authenticatedPage.goto('/dashboard');
  await axeScan(authenticatedPage); // fails on critical violations
});
```

- `authenticatedPage` — logs in via `POST http://localhost:8000/api/v1/auth/login`
  (override host with `PLAYWRIGHT_API_BASE_URL`), then sets the `cf_session`
  cookie and `localStorage.access_token` before navigation.
- `axeScan(page)` — runs `@axe-core/playwright` with WCAG 2.1 A/AA tags and
  throws if any violation has `impact === 'critical'`.

## Environment variables

| Name | Default | Purpose |
|------|---------|---------|
| `PLAYWRIGHT_API_BASE_URL` | `http://localhost:8000` | Backend used by `authenticatedPage`. |
| `PLAYWRIGHT_TEST_EMAIL` | `e2e+test@contentflow.dev` | Seed user email. |
| `PLAYWRIGHT_TEST_PASSWORD` | `TestPassword123!` | Seed user password. |
| `RUN_TIER_3` | unset | Set to `1` to unskip tier-3 auth specs. |
| `CI` | unset | Enables retries (2), reduces workers (2), forbids `.only`. |

## Reports & artifacts

- HTML report: `apps/web/playwright-report/index.html` (open after a run).
- Traces / screenshots / videos on failure: `apps/web/test-results/`.
- Both are gitignored.

## CI checklist

1. `pnpm install --frozen-lockfile`
2. `pnpm --filter @contentflow/web build` (or skip and rely on `pnpm dev`)
3. `pnpm --filter @contentflow/web playwright:install --with-deps`
4. `pnpm --filter @contentflow/web test:e2e`
5. Upload `apps/web/playwright-report/` and `apps/web/test-results/` as
   build artifacts.
