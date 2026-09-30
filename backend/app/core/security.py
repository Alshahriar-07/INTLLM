"""Security primitives: API key generation, hashing and verification.

Raw keys are shown to the user exactly once at creation time and are never
stored. Only a salted scrypt hash plus a short fingerprint is persisted.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

KEY_PREFIX = "intllm_"
# scrypt parameters (n, r, p). Chosen for ~16 MB / ~50 ms on typical hardware.
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_DKLEN = 32


def generate_api_key() -> str:
    """Return a high-entropy raw API key. Never store this value."""
    return f"{KEY_PREFIX}{secrets.token_urlsafe(32)}"


def key_fingerprint(raw_key: str) -> str:
    """A stable, non-reversible short fingerprint for display/audit."""
    digest = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    return digest[:12]


def hash_api_key(raw_key: str, salt: bytes | None = None) -> tuple[str, str]:
    """Hash a raw key. Returns ``(salt_hex, hash_hex)``."""
    salt = salt or secrets.token_bytes(16)
    derived = hashlib.scrypt(
        raw_key.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_SCRYPT_DKLEN,
    )
    return salt.hex(), derived.hex()


def verify_api_key(raw_key: str, salt_hex: str, expected_hash_hex: str) -> bool:
    try:
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(expected_hash_hex)
    except ValueError:
        return False
    derived = hashlib.scrypt(
        raw_key.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=len(expected) or _SCRYPT_DKLEN,
    )
    return hmac.compare_digest(derived, expected)


def redact_key(raw_key: str) -> str:
    """Return a masked representation safe for logs and UI."""
    if len(raw_key) <= len(KEY_PREFIX) + 4:
        return f"{KEY_PREFIX}****"
    return f"{raw_key[: len(KEY_PREFIX) + 4]}...{raw_key[-4:]}"
