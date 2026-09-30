"""API key hashing and secret redaction."""

from __future__ import annotations

from app.core.logging import redact
from app.core.security import (
    generate_api_key,
    hash_api_key,
    key_fingerprint,
    redact_key,
    verify_api_key,
)


def test_generated_key_has_prefix_and_entropy():
    key = generate_api_key()
    assert key.startswith("intllm_")
    assert len(key) > 32
    assert generate_api_key() != key


def test_hash_verify_roundtrip():
    key = generate_api_key()
    salt, digest = hash_api_key(key)
    assert verify_api_key(key, salt, digest) is True
    assert verify_api_key("intllm_wrong", salt, digest) is False


def test_fingerprint_is_stable_and_not_the_key():
    key = generate_api_key()
    fingerprint = key_fingerprint(key)
    assert fingerprint == key_fingerprint(key)
    assert fingerprint not in key


def test_redact_key_masks_secret():
    key = generate_api_key()
    masked = redact_key(key)
    assert key not in masked
    assert masked.startswith("intllm_")


def test_log_redaction_strips_keys_and_bearer_tokens():
    key = generate_api_key()
    assert key not in redact(f"using {key}")
    assert "secret-token" not in redact("Authorization: Bearer secret-token")
    assert redact({"api_key": key})["api_key"] == "***redacted***"
