FROM node:20-alpine

WORKDIR /app

ENV NEXT_TELEMETRY_DISABLED=1

RUN corepack enable

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml turbo.json ./
COPY apps/web/package.json apps/web/package.json
COPY packages/api-client/package.json packages/api-client/package.json
COPY packages/types/package.json packages/types/package.json
COPY packages/typescript-config/package.json packages/typescript-config/package.json

RUN pnpm install --frozen-lockfile

COPY apps/web apps/web
COPY packages packages

RUN pnpm --filter @contentflow/types build && \
    pnpm --filter @contentflow/api-client build

EXPOSE 3000

CMD ["pnpm", "--filter", "@contentflow/web", "dev", "--hostname", "0.0.0.0"]
