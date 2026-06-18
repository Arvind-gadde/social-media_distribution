"""Whisper transcription service.

Two backends:
  * ``openai`` (default) — calls the hosted OpenAI Whisper endpoint via the
    ``openai`` SDK, useful for production with no GPU.
  * ``local`` — loads a local ``faster-whisper`` model from disk for
    air-gapped / GPU-equipped deployments.

Callers stay backend-agnostic via :class:`WhisperService.transcribe`.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import httpx
import structlog

from app.config import get_settings

log = structlog.get_logger(__name__)

settings = get_settings()


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str


@dataclass
class TranscriptionResult:
    text: str
    language: str | None = None
    duration: float | None = None
    segments: list[TranscriptSegment] = field(default_factory=list)
    backend: str = ""


class WhisperService:
    def __init__(
        self,
        *,
        provider: str | None = None,
        model: str | None = None,
        openai_client: Any | None = None,
        local_model: Any | None = None,
    ) -> None:
        self.provider = (provider or settings.WHISPER_PROVIDER).lower()
        self.model = model or settings.WHISPER_MODEL
        self._openai_client = openai_client
        self._local_model = local_model

    @property
    def is_available(self) -> bool:
        return settings.has_whisper or self._openai_client is not None or self._local_model is not None

    # ── public API ─────────────────────────────────────────────────────

    async def transcribe_url(self, audio_url: str, *, language: str | None = None) -> TranscriptionResult:
        audio_bytes, suffix = await self._download(audio_url)
        return await self.transcribe_bytes(audio_bytes, filename=f"audio{suffix}", language=language)

    async def transcribe_bytes(
        self,
        audio_bytes: bytes,
        *,
        filename: str = "audio.mp3",
        language: str | None = None,
    ) -> TranscriptionResult:
        if not self.is_available:
            raise RuntimeError("Whisper backend not configured")
        if self.provider == "local":
            return await self._transcribe_local(audio_bytes, language=language)
        return await self._transcribe_openai(audio_bytes, filename=filename, language=language)

    # ── backends ───────────────────────────────────────────────────────

    async def _transcribe_openai(
        self,
        audio_bytes: bytes,
        *,
        filename: str,
        language: str | None,
    ) -> TranscriptionResult:
        client = self._openai_client or self._build_openai_client()

        def _run() -> Any:
            kwargs: dict[str, Any] = {
                "model": self.model,
                "file": (filename, audio_bytes),
                "response_format": "verbose_json",
            }
            if language:
                kwargs["language"] = language
            return client.audio.transcriptions.create(**kwargs)

        response = await asyncio.to_thread(_run)
        return self._normalize_openai_response(response)

    async def _transcribe_local(self, audio_bytes: bytes, *, language: str | None) -> TranscriptionResult:
        model = self._local_model or self._build_local_model()
        import tempfile, os

        def _run() -> dict[str, Any]:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name
            try:
                segments, info = model.transcribe(tmp_path, language=language)
                segs = [
                    TranscriptSegment(start=float(s.start), end=float(s.end), text=s.text)
                    for s in segments
                ]
                full_text = " ".join(s.text.strip() for s in segs)
                return {
                    "text": full_text,
                    "language": getattr(info, "language", None),
                    "duration": getattr(info, "duration", None),
                    "segments": segs,
                }
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

        data = await asyncio.to_thread(_run)
        return TranscriptionResult(
            text=data["text"],
            language=data["language"],
            duration=data["duration"],
            segments=data["segments"],
            backend="local",
        )

    # ── helpers ────────────────────────────────────────────────────────

    def _build_openai_client(self) -> Any:
        try:
            from openai import OpenAI  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("openai package not installed") from exc
        return OpenAI(api_key=settings.OPENAI_API_KEY)

    def _build_local_model(self) -> Any:
        try:
            from faster_whisper import WhisperModel  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("faster-whisper not installed") from exc
        return WhisperModel(settings.WHISPER_LOCAL_MODEL_PATH or self.model)

    @staticmethod
    def _normalize_openai_response(response: Any) -> TranscriptionResult:
        data = response if isinstance(response, dict) else getattr(response, "model_dump", lambda: response)()
        if not isinstance(data, dict):
            data = {"text": str(response)}
        segs = []
        for s in data.get("segments") or []:
            segs.append(
                TranscriptSegment(
                    start=float(s.get("start", 0.0)),
                    end=float(s.get("end", 0.0)),
                    text=str(s.get("text", "")),
                )
            )
        return TranscriptionResult(
            text=str(data.get("text", "")).strip(),
            language=data.get("language"),
            duration=data.get("duration"),
            segments=segs,
            backend="openai",
        )

    @staticmethod
    async def _download(url: str) -> tuple[bytes, str]:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            ctype = (resp.headers.get("content-type") or "").lower()
            suffix = ".mp3"
            if "wav" in ctype:
                suffix = ".wav"
            elif "mp4" in ctype or "m4a" in ctype:
                suffix = ".m4a"
            elif "ogg" in ctype:
                suffix = ".ogg"
            return resp.content, suffix
