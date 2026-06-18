"""Unit tests for the per-platform webhook payload parsers.

End-to-end ``reconcile_receipt`` is exercised by the DB-bound integration tests
(when Postgres is available). These tests pin the pure-Python extraction logic.
"""
from __future__ import annotations

import pytest

from app.services import webhook_reconciliation as wr


def test_unknown_platform_returns_empty():
    parsed = wr.parse_payload("myspace", {"any": "thing"})
    assert parsed.platform_post_id is None
    assert parsed.metrics == {}


def test_instagram_parser_extracts_metrics_and_media_id():
    payload = {
        "entry": [
            {
                "id": "ig-acct",
                "changes": [
                    {
                        "value": {
                            "media_id": "ig-media-1",
                            "impressions": 500,
                            "like_count": 42,
                            "comments_count": 7,
                            "saved": 3,
                        }
                    }
                ],
            }
        ]
    }
    parsed = wr.parse_payload("instagram", payload)
    assert parsed.platform_post_id == "ig-media-1"
    assert parsed.metrics == {
        "views": 500,
        "likes": 42,
        "comments": 7,
        "saves": 3,
    }


def test_instagram_falls_back_to_reach_when_no_impressions():
    payload = {
        "entry": [
            {
                "id": "ig-acct",
                "changes": [{"value": {"media_id": "m1", "reach": 100}}],
            }
        ]
    }
    parsed = wr.parse_payload("instagram", payload)
    assert parsed.metrics["views"] == 100


def test_youtube_parser_extracts_video_id_only():
    payload = {"resourceId": {"videoId": "yt-vid-9"}}
    parsed = wr.parse_payload("youtube", payload)
    assert parsed.platform_post_id == "yt-vid-9"
    assert parsed.metrics == {}


def test_twitter_parser_normalizes_public_metrics():
    payload = {
        "tweet_metrics_events": [
            {
                "id_str": "tw-1",
                "public_metrics": {
                    "impression_count": 999,
                    "like_count": 50,
                    "reply_count": 4,
                    "retweet_count": 12,
                },
            }
        ]
    }
    parsed = wr.parse_payload("twitter", payload)
    assert parsed.platform_post_id == "tw-1"
    assert parsed.metrics == {
        "views": 999,
        "likes": 50,
        "comments": 4,
        "shares": 12,
    }


def test_twitter_parser_handles_create_event_with_favorite_count():
    payload = {
        "tweet_create_events": [
            {"id_str": "tw-2", "favorite_count": 10, "retweet_count": 1}
        ]
    }
    parsed = wr.parse_payload("twitter", payload)
    assert parsed.metrics["likes"] == 10
    assert parsed.metrics["shares"] == 1


def test_linkedin_parser_extracts_total_share_statistics():
    payload = {
        "activity": {
            "ugcPostUrn": "urn:li:ugcPost:1",
            "totalShareStatistics": {
                "likeCount": 11,
                "commentCount": 2,
                "shareCount": 5,
                "impressionCount": 300,
            },
        }
    }
    parsed = wr.parse_payload("linkedin", payload)
    assert parsed.platform_post_id == "urn:li:ugcPost:1"
    assert parsed.metrics == {
        "likes": 11,
        "comments": 2,
        "shares": 5,
        "views": 300,
    }


def test_tiktok_parser_handles_nested_data_metrics():
    payload = {
        "data": {
            "publish_id": "tt-publish-7",
            "metrics": {
                "view_count": 1200,
                "like_count": 80,
                "comment_count": 6,
                "share_count": 14,
            },
        }
    }
    parsed = wr.parse_payload("tiktok", payload)
    assert parsed.platform_post_id == "tt-publish-7"
    assert parsed.metrics == {
        "views": 1200,
        "likes": 80,
        "comments": 6,
        "shares": 14,
    }


def test_tiktok_parser_falls_back_to_flat_fields():
    payload = {
        "publish_id": "tt-flat",
        "view_count": 9,
    }
    parsed = wr.parse_payload("tiktok", {"data": payload})
    assert parsed.platform_post_id == "tt-flat"
    assert parsed.metrics["views"] == 9


def test_engagement_rate_formula():
    rate = wr._engagement_rate({
        "views": 1000,
        "likes": 100,
        "comments": 25,
        "shares": 10,
        "saves": 5,
    })
    # (100+25+10+5) / 1000 = 0.14
    assert rate == 0.14


def test_engagement_rate_clamps_zero_views_to_one():
    rate = wr._engagement_rate({"views": 0, "likes": 5})
    assert rate == 5.0


def test_parse_payload_ignores_non_dict_payload():
    assert wr.parse_payload("instagram", None).metrics == {}
    assert wr.parse_payload("instagram", "garbage").metrics == {}
