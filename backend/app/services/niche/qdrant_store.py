"""Qdrant-backed vector store for niche / topic embeddings.

The wrapper is intentionally thin: the goal is to give callers a stable
async-friendly surface (``upsert`` / ``search`` / ``delete``) without leaking
``qdrant-client`` types into the rest of the codebase, and to degrade
gracefully when Qdrant is not configured.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Iterable

import structlog

from app.config import get_settings

log = structlog.get_logger(__name__)

settings = get_settings()


@dataclass
class NicheVector:
    id: str
    embedding: list[float]
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchHit:
    id: str
    score: float
    payload: dict[str, Any]


class QdrantStore:
    """Async-friendly wrapper around the qdrant-client SDK.

    The underlying SDK is synchronous; this class runs calls in a thread so the
    event loop is not blocked. Methods raise ``RuntimeError`` only when callers
    explicitly opt into Qdrant via ``settings.has_qdrant`` and the import
    fails; otherwise ``is_available`` short-circuits.
    """

    def __init__(
        self,
        collection: str | None = None,
        *,
        client: Any | None = None,
        vector_size: int | None = None,
    ) -> None:
        self.collection = collection or settings.QDRANT_COLLECTION_NICHE
        self.vector_size = vector_size or settings.QDRANT_VECTOR_SIZE
        self._client = client
        self._initialized = client is not None

    # ── lifecycle ──────────────────────────────────────────────────────

    @property
    def is_available(self) -> bool:
        return settings.has_qdrant or self._client is not None

    def _ensure_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not settings.has_qdrant:
            raise RuntimeError("Qdrant is not configured (QDRANT_URL missing)")
        try:
            from qdrant_client import QdrantClient  # type: ignore
        except ImportError as exc:  # pragma: no cover — dev-time guard
            raise RuntimeError("qdrant-client not installed") from exc
        self._client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY or None,
        )
        return self._client

    async def ensure_collection(self) -> None:
        """Create the collection if missing. Idempotent."""
        if not self.is_available:
            return

        def _create() -> None:
            from qdrant_client.http.models import Distance, VectorParams  # type: ignore

            client = self._ensure_client()
            collections = {c.name for c in client.get_collections().collections}
            if self.collection in collections:
                return
            client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
            )

        await asyncio.to_thread(_create)
        if not self._initialized:
            log.info("qdrant_collection_ready", collection=self.collection)
            self._initialized = True

    # ── writes ─────────────────────────────────────────────────────────

    async def upsert(self, vectors: Iterable[NicheVector]) -> int:
        items = list(vectors)
        if not items:
            return 0
        if not self.is_available:
            log.debug("qdrant_upsert_skipped_disabled")
            return 0
        await self.ensure_collection()

        def _upsert() -> int:
            from qdrant_client.http.models import PointStruct  # type: ignore

            client = self._ensure_client()
            points = [
                PointStruct(id=v.id, vector=v.embedding, payload=v.payload)
                for v in items
            ]
            client.upsert(collection_name=self.collection, points=points, wait=True)
            return len(points)

        count = await asyncio.to_thread(_upsert)
        log.info("qdrant_upsert", collection=self.collection, count=count)
        return count

    async def delete(self, ids: Iterable[str]) -> None:
        ids = list(ids)
        if not ids or not self.is_available:
            return

        def _delete() -> None:
            from qdrant_client.http.models import PointIdsList  # type: ignore

            client = self._ensure_client()
            client.delete(
                collection_name=self.collection,
                points_selector=PointIdsList(points=ids),
                wait=True,
            )

        await asyncio.to_thread(_delete)

    # ── reads ──────────────────────────────────────────────────────────

    async def search(
        self,
        embedding: list[float],
        *,
        limit: int = 10,
        score_threshold: float | None = None,
        filter_payload: dict[str, Any] | None = None,
    ) -> list[SearchHit]:
        if not self.is_available:
            return []

        def _search() -> list[SearchHit]:
            from qdrant_client.http.models import (  # type: ignore
                FieldCondition,
                Filter,
                MatchValue,
            )

            client = self._ensure_client()
            qfilter = None
            if filter_payload:
                qfilter = Filter(
                    must=[
                        FieldCondition(key=k, match=MatchValue(value=v))
                        for k, v in filter_payload.items()
                    ]
                )
            res = client.search(
                collection_name=self.collection,
                query_vector=embedding,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=qfilter,
            )
            return [
                SearchHit(id=str(p.id), score=float(p.score), payload=dict(p.payload or {}))
                for p in res
            ]

        return await asyncio.to_thread(_search)
