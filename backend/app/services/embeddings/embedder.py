"""Text embedding service.

Wraps OpenAI's embeddings API (``text-embedding-3-small`` by default, 1536
dimensions) behind a small async surface. Supports batching, deterministic
caching via Redis, and graceful no-op when the OpenAI key is missing — callers
should check ``Embedder.is_available`` before relying on results.

The default model dimension MUST match ``settings.QDRANT_VECTOR_SIZE``;
otherwise upserts to the Qdrant collection will fail.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
from typing import Iterable, Sequence

import structlog

from app.config import get_settings

log = structlog.get_logger(__name__)


class EmbeddingError(RuntimeError):
    """Raised when an embedding call fails and the caller asked us to be strict."""


class Embedder:
    """Generate dense vector embeddings for arbitrary text.

    Designed for dependency injection — pass a ``client`` in tests to avoid
    real network calls. In production the singleton from :func:`get_embedder`
    is used everywhere.
    """

    def __init__(
        self,
        *,
        client: object | None = None,
        model: str | None = None,
        batch_size: int | None = None,
        redis_client: object | None = None,
    ) -> None:
        settings = get_settings()
        self._provider = settings.EMBEDDING_PROVIDER
        self._model = model or settings.EMBEDDING_MODEL
        self._batch_size = batch_size or settings.EMBEDDING_BATCH_SIZE
        self._cache_ttl = settings.EMBEDDING_CACHE_TTL
        self._dim = settings.QDRANT_VECTOR_SIZE
        self._client = client
        self._redis = redis_client
        self._has_key = bool(settings.OPENAI_API_KEY) or client is not None

    @property
    def is_available(self) -> bool:
        return self._has_key

    @property
    def model(self) -> str:
        return self._model

    @property
    def dimension(self) -> int:
        return self._dim

    # ── public api ────────────────────────────────────────────────────────

    async def embed(self, text: str) -> list[float] | None:
        """Embed a single string. Returns ``None`` if the service is disabled."""
        if not text or not text.strip():
            return None
        results = await self.embed_many([text])
        return results[0] if results else None

    async def embed_many(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed many strings with caching + batching. Order preserved.

        Strings that are empty/whitespace are replaced with a zero vector so
        the output length always matches the input length — callers that care
        about that contract don't need to dedupe upstream.
        """
        if not texts:
            return []
        if not self.is_available:
            log.debug("embed_skipped_no_key", count=len(texts))
            return [[0.0] * self._dim for _ in texts]

        normalised = [t.strip() if t else "" for t in texts]
        cached, misses, miss_idx = await self._lookup_cache(normalised)
        if misses:
            fresh = await self._embed_batches(misses)
            await self._store_cache(misses, fresh)
            for idx, vec in zip(miss_idx, fresh):
                cached[idx] = vec
        # Replace any None (originally-empty) entries with a zero vector.
        return [vec if vec is not None else [0.0] * self._dim for vec in cached]

    # ── internals ─────────────────────────────────────────────────────────

    async def _embed_batches(self, inputs: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for start in range(0, len(inputs), self._batch_size):
            batch = inputs[start : start + self._batch_size]
            out.extend(await self._call_openai(batch))
        return out

    async def _call_openai(self, batch: list[str]) -> list[list[float]]:
        client = self._ensure_client()
        try:
            response = await client.embeddings.create(model=self._model, input=batch)
        except Exception as exc:  # network / auth / rate limit
            log.error("embed_call_failed", model=self._model, error=str(exc))
            raise EmbeddingError(str(exc)) from exc

        vectors = [list(item.embedding) for item in response.data]
        if vectors and len(vectors[0]) != self._dim:
            raise EmbeddingError(
                f"embedding dim mismatch: model returned {len(vectors[0])}, "
                f"QDRANT_VECTOR_SIZE={self._dim}"
            )
        return vectors

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        try:
            from openai import AsyncOpenAI  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise EmbeddingError("openai package not installed") from exc
        settings = get_settings()
        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    # ── cache (Redis) ─────────────────────────────────────────────────────

    def _cache_key(self, text: str) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"emb:{self._model}:{digest}"

    async def _lookup_cache(
        self, inputs: list[str]
    ) -> tuple[list[list[float] | None], list[str], list[int]]:
        """Return (preallocated_result, miss_texts, miss_indices).

        Empty strings short-circuit to ``None`` so callers can replace them
        with zero vectors after the batch returns.
        """
        result: list[list[float] | None] = [None] * len(inputs)
        miss_texts: list[str] = []
        miss_idx: list[int] = []
        redis = await self._get_redis()
        for i, text in enumerate(inputs):
            if not text:
                continue
            if redis is None:
                miss_texts.append(text)
                miss_idx.append(i)
                continue
            try:
                raw = await redis.get(self._cache_key(text))
            except Exception as exc:  # treat Redis as best-effort
                log.warning("embed_cache_get_failed", error=str(exc))
                raw = None
            if raw:
                try:
                    result[i] = json.loads(raw)
                    continue
                except (ValueError, TypeError):
                    pass
            miss_texts.append(text)
            miss_idx.append(i)
        return result, miss_texts, miss_idx

    async def _store_cache(
        self, texts: list[str], vectors: list[list[float]]
    ) -> None:
        redis = await self._get_redis()
        if redis is None or not texts:
            return
        try:
            pipe = redis.pipeline()
            for text, vec in zip(texts, vectors):
                pipe.set(self._cache_key(text), json.dumps(vec), ex=self._cache_ttl)
            await pipe.execute()
        except Exception as exc:
            log.warning("embed_cache_set_failed", error=str(exc))

    async def _get_redis(self):
        # ``False`` is an explicit sentinel for "cache disabled" used in tests
        # and pure-DI callers. Truthy objects are returned as-is; ``None``
        # triggers lazy loading from the shared cache manager.
        if self._redis is False:
            return None
        if self._redis is not None:
            return self._redis
        try:
            from app.services.cache import get_cache_manager

            self._redis = get_cache_manager().redis
        except Exception:
            self._redis = None
        return self._redis


# ── module-level singleton ────────────────────────────────────────────────

_embedder: Embedder | None = None
_lock = asyncio.Lock()


def get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder


async def embed_text(text: str) -> list[float] | None:
    """Convenience: embed a single string via the singleton embedder."""
    return await get_embedder().embed(text)


async def embed_texts(texts: Iterable[str]) -> list[list[float]]:
    """Convenience: embed many strings via the singleton embedder."""
    return await get_embedder().embed_many(list(texts))
