# ─────────────────────────────────────────────────────────────────────────────
# ContentFlow API — Production Dockerfile
# Multi-stage build with: dependency caching, non-root user, health check
# ─────────────────────────────────────────────────────────────────────────────

# Stage 1: Builder — install Python deps with build tools
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build-time system deps (removed in final image)
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt \
    && pip install --no-cache-dir --no-deps --prefix=/install google-generativeai==0.8.5 \
    && pip install --no-cache-dir --prefix=/install httplib2 google-api-python-client


# Stage 2: Runtime — minimal image with only runtime deps
FROM python:3.12-slim AS runtime

# Labels for container metadata
LABEL maintainer="contentflow-team" \
      app="contentflow-api" \
      version="2.0"

# Install only runtime system deps
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 \
        ffmpeg \
        curl \
        tini \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get purge -y --auto-remove

# Create non-root user
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash appuser

WORKDIR /app

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY --chown=appuser:appuser . .

# Create necessary directories
RUN mkdir -p /app/logs /app/tmp \
    && chown -R appuser:appuser /app/logs /app/tmp

# Switch to non-root user
USER appuser

# Environment defaults (override via docker-compose / k8s)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PORT=8000

# Expose API port
EXPOSE ${PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Use tini as init system (proper signal handling)
ENTRYPOINT ["tini", "--"]

# Default: run migrations then start uvicorn
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 2 --loop uvloop --http httptools --access-log"]
