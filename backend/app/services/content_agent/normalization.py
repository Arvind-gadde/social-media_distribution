"""Helpers for normalising model-generated content payloads."""

from __future__ import annotations

import re
from typing import Any


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (list, tuple, set)):
        return "\n".join(text for item in value if (text := _coerce_text(item)))
    return str(value).strip()


def _coerce_text_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [text for item in value if (text := _coerce_text(item))]
    if isinstance(value, str):
        parts = [
            part.strip(" -\t")
            for part in re.split(r"(?:\r?\n|;)+", value)
        ]
        items = [part for part in parts if part]
        return items if items else [_coerce_text(value)]
    text = _coerce_text(value)
    return [text] if text else []


def _coerce_hashtags(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        parts = [_coerce_text(item) for item in value]
    elif isinstance(value, str):
        hashtag_matches = re.findall(r"#(?:[A-Za-z0-9_][A-Za-z0-9_-]*)", value)
        if hashtag_matches:
            parts = hashtag_matches
        else:
            parts = [part.strip() for part in re.split(r"[\s,\r\n;]+", value)]
    else:
        parts = [_coerce_text(value)]

    deduped: list[str] = []
    seen: set[str] = set()
    for part in parts:
        if not part:
            continue
        slug = re.sub(r"[^A-Za-z0-9_-]", "", part.lstrip("#"))
        if not slug:
            continue
        cleaned = f"#{slug}"
        if cleaned not in seen:
            seen.add(cleaned)
            deduped.append(cleaned)
    return deduped


def normalize_generated_content(payload: dict[str, Any] | None) -> dict[str, Any]:
    data = dict(payload or {})
    return {
        "hook": _coerce_text(data.get("hook")),
        "caption": _coerce_text(data.get("caption")),
        "hashtags": _coerce_hashtags(data.get("hashtags")),
        "call_to_action": _coerce_text(data.get("call_to_action")),
        "thread_tweets": _coerce_text_list(data.get("thread_tweets")),
        "script_outline": _coerce_text(data.get("script_outline")),
        "engagement_tips": _coerce_text_list(data.get("engagement_tips")),
    }
