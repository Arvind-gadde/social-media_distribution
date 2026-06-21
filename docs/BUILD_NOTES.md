# Frontend image build — notes & fixes

The `frontend` Docker image (`docker compose build frontend`) was **never buildable** in this
checkout. Diagnosed + fixed a chain of pre-existing issues; one final blocker needs the missing
source layer restored.

## Fixes applied (this branch)
1. **`.dockerignore` (added)** — there was none, so `COPY apps/web` / `COPY packages` pulled the
   **host `node_modules`** (Windows symlinks) into the image, leaving every per-package `.bin` shim
   (`next`, `tsc`) dangling. Now excludes `node_modules`, `.next`, `dist`, `.env`, etc.
2. **Dockerfile: `COPY … .npmrc`** — the repo's `.npmrc` (`node-linker=hoisted`, required by
   Expo/Metro) wasn't copied before `pnpm install`, so the install layout differed from local.
3. **Dockerfile: `pnpm install --prod=false`** — `ENV NODE_ENV=production` (set above the install)
   made pnpm skip devDependencies, so `typescript`/`next` weren't installed for the build.
4. **transpilePackages + `src` entry points** — `@contentflow/types` & `@contentflow/api-client`
   now point `main`/`types` at `./src/index.ts` and are listed in `next.config` `transpilePackages`,
   so `next build` compiles them directly. Removed the fragile per-package `tsc` pre-build from the
   Dockerfile (it broke under the hoisted layout).
5. **`apps/web/tsconfig.json`: `baseUrl: "."`** — `paths` (`@/*`) had no `baseUrl`, so webpack
   couldn't resolve the `@/` alias during a production build.

## Remaining blocker — restore `apps/web/src/lib/`
`.gitignore` line ~85 has the standard Python `lib/` rule, which **also matches
`apps/web/src/lib/`**. That whole utility layer was therefore never committed and is **absent from
this checkout**. The web imports these 8 modules that do not exist here:

```
@/lib/utils            (cn, getNicheColor, formatters)
@/lib/api              (api client config)
@/lib/toast
@/lib/session
@/lib/safe-redirect
@/lib/query-client
@/lib/command-bar-context
@/lib/websocket
```

`.gitignore` is now fixed (`!apps/web/src/lib/`) so once the files exist they get tracked. **Action
needed:** restore `apps/web/src/lib/` from the original dev machine (where it exists locally, gitignored),
then `docker compose build frontend` should succeed end-to-end. If the originals are unavailable, the
layer can be reconstructed from its usage across `apps/web/src`.

## Verify after restoring
```bash
docker compose build frontend     # expect: Compiled successfully + Route (app) table
docker compose up -d               # full stack
```
