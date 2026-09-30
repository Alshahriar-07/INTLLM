"""Memory scoring/TTL helpers and web SSRF guard."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.core.errors import ValidationError
from app.services.brain.service import (
    extract_keywords,
    freshness_score,
    normalize_content,
)
from app.services.web.service import guard_url, trust_for


def test_normalize_content_collapses_whitespace():
    assert normalize_content("  Hello   World\n") == "hello world"


def test_extract_keywords_filters_stopwords_and_dupes():
    keywords = extract_keywords("How do I configure PostgreSQL postgresql database")
    assert "configure" in keywords
    assert "postgresql" in keywords
    assert "how" not in keywords
    assert len(keywords) == len(set(keywords))


def test_freshness_decays_to_zero_after_ttl():
    now = datetime.now(timezone.utc)
    fresh = freshness_score(
        verified_at=now, created_at=now, policy="medium", now=now
    )
    assert fresh == 100.0
    stale = freshness_score(
        verified_at=now - timedelta(days=60), created_at=now, policy="medium", now=now
    )
    assert stale == 0.0


def test_freshness_halfway_through_ttl():
    now = datetime.now(timezone.utc)
    score = freshness_score(
        verified_at=now - timedelta(days=15), created_at=now, policy="medium", now=now
    )
    assert 45 <= score <= 55


def test_guard_url_rejects_non_http_and_localhost():
    with pytest.raises(ValidationError):
        guard_url("file:///etc/passwd")
    with pytest.raises(ValidationError):
        guard_url("http://localhost:8000/secret")
    with pytest.raises(ValidationError):
        guard_url("http://127.0.0.1/")


def test_trust_for_known_domain():
    assert trust_for("docs.python.org") >= 90
    assert trust_for("example.com") == 65
