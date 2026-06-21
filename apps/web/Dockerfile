# ─────────────────────────────────────────────────────────────────────────────
# ContentFlow Web — Production Dockerfile
# Installs deps, builds shared packages + the Next.js app, serves with `next start`.
# (Previously ran `next dev` — a dev server in production leaks stack traces via
#  the error overlay, skips optimization/minification, and is unstable under load.)
# ─────────────────────────────────────────────────────────────────────────────
FROM node:20-alpine

WORKDIR /app

ENV NEXT_TELEMETRY_DISABLED=1 \
    NODE_ENV=production

# NEXT_PUBLIC_* AND the rewrite target (BACKEND_URL) are baked at BUILD time by
# Next.js — they MUST be present during `next build`, not just at runtime.
# Override per environment via docker-compose `build.args`.
ARG NEXT_PUBLIC_API_URL=""
ARG NEXT_PUBLIC_WS_URL=""
ARG BACKEND_URL="http://localhost:8000"
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_PUBLIC_WS_URL=$NEXT_PUBLIC_WS_URL \
    BACKEND_URL=$BACKEND_URL

RUN corepack enable

# ── Dependencies (cached layer) ──────────────────────────────────────────────
# .npmrc carries node-linker=hoisted + shamefully-hoist — without it pnpm falls
# back to the symlinked layout and the per-package `tsc` bin shim breaks at build.
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml turbo.json .npmrc ./
COPY apps/web/package.json apps/web/package.json
COPY packages/api-client/package.json packages/api-client/package.json
COPY packages/types/package.json packages/types/package.json
COPY packages/typescript-config/package.json packages/typescript-config/package.json
COPY patches patches

# --prod=false: NODE_ENV=production (set above) would otherwise skip devDependencies,
# but the build needs them (typescript/tsc, next, etc.). Runtime still runs production.
RUN pnpm install --frozen-lockfile --prod=false

# ── Build ────────────────────────────────────────────────────────────────────
COPY apps/web apps/web
COPY packages packages

# Build the shared TS packages with the hoisted root tsc (`pnpm exec`) instead of
# the per-package `build` script: under node-linker=hoisted the per-package
# node_modules/.bin/tsc shim is a dangling symlink, so `pnpm --filter X build`
# (which runs `tsc` via that shim) fails to resolve typescript.
# The shared TS packages (@contentflow/types, @contentflow/api-client) point their
# entry at src and are listed in next.config transpilePackages, so `next build`
# compiles them directly — no fragile per-package `tsc` pre-build (which broke
# under the Expo-required node-linker=hoisted layout).
RUN pnpm --filter @contentflow/web build

EXPOSE 3000

# Production server (optimized build, no dev overlay).
CMD ["pnpm", "--filter", "@contentflow/web", "start", "--hostname", "0.0.0.0"]
