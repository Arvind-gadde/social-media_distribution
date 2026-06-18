"""Tests for the embedding service."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.embeddings.embedder import Embedder, EmbeddingError


def _fake_openai_client(vectors: list[list[float]]):
    """Build an object that mimics ``AsyncOpenAI``'s ``embeddings.create``."""
    data = [SimpleNamespace(embedding=v) for v in vectors]
    response = SimpleNamespace(data=data)
    create = AsyncMock(return_value=response)
    return SimpleNamespace(embeddings=SimpleNamespace(create=create)), create


@pytest.mark.asyncio
async def test_embed_returns_vector_when_client_available():
    client, _ = _fake_openai_client([[0.1] * 1536])
    embedder = Embedder(client=client, redis_client=False)  # disable cache
    vec = await embedder.embed("hello world")
    assert vec == [0.1] * 1536


@pytest.mark.asyncio
async def test_embed_many_preserves_order_and_handles_empty():
    client, create = _fake_openai_client([[0.2] * 1536, [0.3] * 1536])
    embedder = Embedder(client=client, redis_client=False)
    out = await embedder.embed_many(["first", "", "second"])
    assert len(out) == 3
    assert out[0] == [0.2] * 1536
    assert out[1] == [0.0] * 1536  # empty → zero vector
    assert out[2] == [0.3] * 1536
    # The empty string should not be sent to OpenAI.
    create.assert_awaited_once()
    sent = create.await_args.kwargs["input"]
    assert sent == ["first", "second"]


@pytest.mark.asyncio
async def test_embed_many_raises_on_dim_mismatch():
    client, _ = _fake_openai_client([[0.0] * 512])  # wrong size
    embedder = Embedder(client=client, redis_client=False)
    with pytest.raises(EmbeddingError):
        await embedder.embed_many(["whatever"])


@pytest.mark.asyncio
async def test_embed_many_zero_vector_when_no_key(monkeypatch):
    from app.services.embeddings import embedder as mod

    embedder = Embedder.__new__(Embedder)
    embedder._provider = "openai"
    embedder._model = "text-embedding-3-small"
    embedder._batch_size = 96
    embedder._cache_ttl = 0
    embedder._dim = 1536
    embedder._client = None
    embedder._redis = False
    embedder._has_key = False  # simulate missing key

    out = await embedder.embed_many(["anything"])
    assert out == [[0.0] * 1536]
