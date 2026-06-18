"""Embeddings service — vector representations of text for semantic search.

Exposes :func:`embed_text` and :func:`embed_texts` plus the high-level
:class:`Embedder` for callers that want to inject a different backend in tests.
"""
from app.services.embeddings.embedder import (
    Embedder,
    EmbeddingError,
    embed_text,
    embed_texts,
    get_embedder,
)

__all__ = [
    "Embedder",
    "EmbeddingError",
    "embed_text",
    "embed_texts",
    "get_embedder",
]
