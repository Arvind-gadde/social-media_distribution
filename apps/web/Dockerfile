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
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml turbo.json ./
COPY apps/web/package.json apps/web/package.json
COPY packages/api-client/package.json packages/api-client/package.json
COPY packages/types/package.json packages/types/package.json
COPY packages/typescript-config/package.json packages/typescript-config/package.json
COPY patches patches

RUN pnpm install --frozen-lockfile

# ── Build ────────────────────────────────────────────────────────────────────
COPY apps/web apps/web
COPY packages packages

RUN pnpm --filter @contentflow/types build \
 && pnpm --filter @contentflow/api-client build \
 && pnpm --filter @contentflow/web build

EXPOSE 3000

# Production server (optimized build, no dev overlay).
CMD ["pnpm", "--filter", "@contentflow/web", "start", "--hostname", "0.0.0.0"]
