"""Index ContentVariant rows into the Qdrant content collection.

Used by the Niche Intelligence Agent (and incrementally by ingestion) to build
a semantic index of a workspace's published content. Once indexed, similarity
search clusters related posts so the agent can infer audience interest beyond
explicit ``content_pillars`` tags.
"""
from __future__ import annotations

from typing import Sequence
from uuid import UUID

import structlog

from app.config import get_settings
from app.domains.execution.models import ContentVariant
from app.services.embeddings import get_embedder
from app.services.niche.qdrant_store import NicheVector, QdrantStore, SearchHit

log = structlog.get_logger(__name__)


def _variant_text(variant: ContentVariant) -> str:
    parts: list[str] = []
    for attr in ("title", "caption", "body", "script"):
        value = getattr(variant, attr, None)
        if value:
            parts.append(str(value))
    pillars = getattr(variant, "content_pillars", None) or []
    if pillars:
        parts.append("Pillars: " + ", ".join(str(p) for p in pillars))
    return "\n".join(parts).strip()


async def index_variants(
    workspace_id: UUID,
    variants: Sequence[ContentVariant],
    *,
    store: QdrantStore | None = None,
) -> int:
    """Embed and upsert content variants. Returns count successfully indexed."""
    settings = get_settings()
    if not settings.has_qdrant or not settings.has_openai:
        log.debug(
            "content_index_skipped",
            qdrant=settings.has_qdrant,
            openai=settings.has_openai,
        )
        return 0
    if not variants:
        return 0

    texts = [_variant_text(v) for v in variants]
    embedder = get_embedder()
    vectors = await embedder.embed_many(texts)

    store = store or QdrantStore(collection=settings.QDRANT_COLLECTION_CONTENT)
    points: list[NicheVector] = []
    for variant, text, vec in zip(variants, texts, vectors):
        if not text or not vec:
            continue
        points.append(
            NicheVector(
                id=str(variant.id),
                embedding=vec,
                payload={
                    "workspace_id": str(workspace_id),
                    "content_project_id": str(variant.content_project_id)
                    if getattr(variant, "content_project_id", None)
                    else None,
                    "platform": getattr(variant, "platform", None),
                    "content_pillars": list(getattr(variant, "content_pillars", []) or []),
                    "engagement_rate": float(getattr(variant, "engagement_rate", 0) or 0),
                    "status": getattr(variant, "status", None),
                },
            )
        )
    return await store.upsert(points)


async def find_similar(
    workspace_id: UUID,
    query: str,
    *,
    limit: int = 10,
    score_threshold: float | None = None,
    store: QdrantStore | None = None,
) -> list[SearchHit]:
    """Search the content collection for variants semantically near ``query``."""
    settings = get_settings()
    if not settings.has_qdrant or not settings.has_openai or not query.strip():
        return []
    embedding = await get_embedder().embed(query)
    if not embedding:
        return []
    store = store or QdrantStore(collection=settings.QDRANT_COLLECTION_CONTENT)
    return await store.search(
        embedding,
        limit=limit,
        score_threshold=score_threshold,
        filter_payload={"workspace_id": str(workspace_id)},
    )
