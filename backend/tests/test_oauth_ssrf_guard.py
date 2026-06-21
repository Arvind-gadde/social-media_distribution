"""Tests for the SSRF guard on the credential-connect endpoints.

Uses IP literals so getaddrinfo resolves them locally (no real DNS / network).
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.api.v1.oauth import _assert_public_http_url


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:5432",       # loopback
        "http://169.254.169.254",      # cloud metadata (link-local)
        "http://10.0.0.5",             # private
        "http://192.168.1.10",         # private
        "http://172.16.0.1",           # private
        "http://[::1]:443",            # ipv6 loopback
        "file:///etc/passwd",          # bad scheme
        "gopher://127.0.0.1",          # bad scheme
        "not-a-url",                   # no host
    ],
)
def test_blocks_ssrf_prone_urls(url):
    with pytest.raises(HTTPException):
        _assert_public_http_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://1.1.1.1",   # public IP literal
        "https://8.8.8.8",   # public IP literal
    ],
)
def test_allows_public_hosts(url):
    # Should not raise.
    _assert_public_http_url(url)
