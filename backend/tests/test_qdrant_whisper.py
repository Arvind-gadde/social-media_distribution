"""Tests for the Qdrant + Whisper integration wrappers."""
from __future__ import annotations

import sys
import types
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _install_qdrant_stub() -> None:
    """qdrant-client is an optional dep — stub the imports our wrapper uses."""
    if "qdrant_client" in sys.modules:
        return
    pkg = types.ModuleType("qdrant_client")
    http_pkg = types.ModuleType("qdrant_client.http")
    models_pkg = types.ModuleType("qdrant_client.http.models")

    class _PointStruct:
        def __init__(self, id, vector, payload):
            self.id = id
            self.vector = vector
            self.payload = payload

    class _Filter:
        def __init__(self, must=None):
            self.must = must or []

    class _FieldCondition:
        def __init__(self, key, match):
            self.key = key
            self.match = match

    class _MatchValue:
        def __init__(self, value):
            self.value = value

    class _PointIdsList:
        def __init__(self, points):
            self.points = points

    class _Distance:
        COSINE = "Cosine"

    class _VectorParams:
        def __init__(self, size, distance):
            self.size = size
            self.distance = distance

    models_pkg.PointStruct = _PointStruct
    models_pkg.Filter = _Filter
    models_pkg.FieldCondition = _FieldCondition
    models_pkg.MatchValue = _MatchValue
    models_pkg.PointIdsList = _PointIdsList
    models_pkg.Distance = _Distance
    models_pkg.VectorParams = _VectorParams
    http_pkg.models = models_pkg
    pkg.http = http_pkg
    pkg.QdrantClient = MagicMock
    sys.modules["qdrant_client"] = pkg
    sys.modules["qdrant_client.http"] = http_pkg
    sys.modules["qdrant_client.http.models"] = models_pkg


_install_qdrant_stub()

from app.services.niche.qdrant_store import NicheVector, QdrantStore, SearchHit  # noqa: E402
from app.services.video.whisper_service import (  # noqa: E402
    TranscriptionResult,
    WhisperService,
)


# ─── Qdrant ────────────────────────────────────────────────────────────────


class _FakeQdrantClient:
    def __init__(self) -> None:
        self.collections = SimpleNamespace(collections=[])
        self.created: list[str] = []
        self.upserted: list[tuple[str, list]] = []
        self.deleted: list[tuple[str, list]] = []
        self.searched: list[tuple[str, list[float], int]] = []
        self._search_hits: list = []

    def get_collections(self) -> SimpleNamespace:
        return self.collections

    def create_collection(self, *, collection_name: str, vectors_config) -> None:
        self.created.append(collection_name)
        self.collections.collections.append(SimpleNamespace(name=collection_name))

    def upsert(self, *, collection_name: str, points, wait: bool) -> None:
        self.upserted.append((collection_name, points))

    def delete(self, *, collection_name: str, points_selector, wait: bool) -> None:
        self.deleted.append((collection_name, points_selector.points))

    def search(self, *, collection_name: str, query_vector, limit, score_threshold, query_filter):
        self.searched.append((collection_name, query_vector, limit))
        return self._search_hits


class TestQdrantStore:
    @pytest.mark.asyncio
    async def test_upsert_creates_collection_on_first_use(self):
        fake = _FakeQdrantClient()
        store = QdrantStore(collection="testcol", client=fake, vector_size=8)
        with patch("app.services.niche.qdrant_store.settings") as cfg:
            cfg.has_qdrant = True
            cfg.QDRANT_COLLECTION_NICHE = "testcol"
            cfg.QDRANT_VECTOR_SIZE = 8
            count = await store.upsert([
                NicheVector(id="n1", embedding=[0.1] * 8, payload={"label": "ai"})
            ])
        assert count == 1
        assert fake.created == ["testcol"]
        assert fake.upserted and fake.upserted[0][0] == "testcol"

    @pytest.mark.asyncio
    async def test_upsert_no_op_when_disabled(self):
        store = QdrantStore(collection="c")
        with patch("app.services.niche.qdrant_store.settings") as cfg:
            cfg.has_qdrant = False
            count = await store.upsert([
                NicheVector(id="n1", embedding=[0.1], payload={})
            ])
        assert count == 0

    @pytest.mark.asyncio
    async def test_search_returns_hits(self):
        fake = _FakeQdrantClient()
        fake._search_hits = [
            SimpleNamespace(id="n1", score=0.91, payload={"label": "fitness"}),
            SimpleNamespace(id="n2", score=0.74, payload={"label": "tech"}),
        ]
        store = QdrantStore(collection="c", client=fake, vector_size=4)
        with patch("app.services.niche.qdrant_store.settings") as cfg:
            cfg.has_qdrant = True
            cfg.QDRANT_COLLECTION_NICHE = "c"
            cfg.QDRANT_VECTOR_SIZE = 4
            hits = await store.search([0.1, 0.2, 0.3, 0.4], limit=5)
        assert [h.id for h in hits] == ["n1", "n2"]
        assert hits[0].score == pytest.approx(0.91)
        assert isinstance(hits[0], SearchHit)

    @pytest.mark.asyncio
    async def test_search_skipped_when_disabled(self):
        store = QdrantStore(collection="c")
        with patch("app.services.niche.qdrant_store.settings") as cfg:
            cfg.has_qdrant = False
            assert await store.search([0.1, 0.2]) == []


# ─── Whisper ───────────────────────────────────────────────────────────────


class TestWhisperService:
    @pytest.mark.asyncio
    async def test_openai_backend_normalizes_response(self):
        fake_client = MagicMock()
        fake_client.audio.transcriptions.create.return_value = {
            "text": "hello world",
            "language": "en",
            "duration": 4.2,
            "segments": [
                {"start": 0.0, "end": 1.5, "text": "hello"},
                {"start": 1.5, "end": 4.0, "text": "world"},
            ],
        }
        svc = WhisperService(provider="openai", model="whisper-1", openai_client=fake_client)
        with patch("app.services.video.whisper_service.settings") as cfg:
            cfg.has_whisper = True
            cfg.WHISPER_PROVIDER = "openai"
            cfg.WHISPER_MODEL = "whisper-1"
            result = await svc.transcribe_bytes(b"FAKE_AUDIO", filename="clip.mp3", language="en")

        assert isinstance(result, TranscriptionResult)
        assert result.text == "hello world"
        assert result.backend == "openai"
        assert len(result.segments) == 2
        kwargs = fake_client.audio.transcriptions.create.call_args.kwargs
        assert kwargs["model"] == "whisper-1"
        assert kwargs["language"] == "en"

    @pytest.mark.asyncio
    async def test_disabled_when_no_backend(self):
        svc = WhisperService(provider="openai")
        with patch("app.services.video.whisper_service.settings") as cfg:
            cfg.has_whisper = False
            cfg.WHISPER_PROVIDER = "openai"
            cfg.WHISPER_MODEL = "whisper-1"
            with pytest.raises(RuntimeError, match="Whisper backend not configured"):
                await svc.transcribe_bytes(b"X")

    @pytest.mark.asyncio
    async def test_transcribe_url_downloads_then_delegates(self):
        fake_client = MagicMock()
        fake_client.audio.transcriptions.create.return_value = {"text": "ok"}
        svc = WhisperService(provider="openai", model="whisper-1", openai_client=fake_client)

        mock_http_resp = MagicMock()
        mock_http_resp.content = b"AUDIO"
        mock_http_resp.headers = {"content-type": "audio/wav"}
        mock_http_resp.raise_for_status = MagicMock()

        http_client = MagicMock()
        http_client.get = AsyncMock(return_value=mock_http_resp)
        http_client.__aenter__ = AsyncMock(return_value=http_client)
        http_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("app.services.video.whisper_service.settings") as cfg,
            patch("app.services.video.whisper_service.httpx.AsyncClient", return_value=http_client),
        ):
            cfg.has_whisper = True
            cfg.WHISPER_PROVIDER = "openai"
            cfg.WHISPER_MODEL = "whisper-1"
            result = await svc.transcribe_url("https://cdn.example/a.wav")

        assert result.text == "ok"
        filename = fake_client.audio.transcriptions.create.call_args.kwargs["file"][0]
        assert filename.endswith(".wav")
