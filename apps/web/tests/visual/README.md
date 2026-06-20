# Visual Regression Snapshots

This directory holds Playwright `toHaveScreenshot()` baselines for ContentFlow web.

## How it works

Playwright writes one PNG per `toHaveScreenshot('name.png')` call, scoped per
project (e.g. `chromium-desktop`, `chromium-mobile`) and per OS. Baselines live
next to the spec file in a `__screenshots__` folder OR under this `tests/visual/`
tree when explicitly configured.

On every `test:e2e` run:
1. Playwright captures the current page.
2. Compares pixel-by-pixel against the committed baseline.
3. Fails if diff exceeds `threshold: 0.02` or `maxDiffPixelRatio: 0.01`
   (see `playwright.config.ts`).
4. Writes `*-actual.png` and `*-diff.png` artifacts to `test-results/` on failure.

## First run / new snapshots

Initial baselines do not exist yet. To generate them:

```powershell
# from repo root
pnpm --filter @contentflow/web playwright:install   # one-time
pnpm --filter @contentflow/web test:e2e -- --update-snapshots
```

Review the generated `*.png` files visually, then commit them.

## Updating a snapshot intentionally

When a design change is approved:

```powershell
pnpm --filter @contentflow/web test:visual -- --update-snapshots
```

Then `git diff` the PNGs (GitHub renders side-by-side) and commit.

## Conventions

- Baseline names are kebab-case: `login.png`, `dashboard-empty.png`.
- Always pass `animations: 'disabled'` and wait for a stable element before
  snapshotting.
- Tag visual tests with `@visual` so `pnpm test:visual` picks them up.
- Mask volatile regions (timestamps, avatars) via `mask: [page.locator(...)]`.

## Cross-platform note

Snapshots are OS-sensitive (font hinting differs Windows vs Linux). CI runs
Linux containers — if you generate baselines on Windows, regenerate them in CI
or rely on Docker for local snapshotting.
