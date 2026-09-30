"""Structured JSON logging with secret redaction.

Never log API keys, passwords, authorization headers or raw bearer tokens.
The redaction filter runs on every record so accidental ``logger.info(header)``
calls cannot leak credentials.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from typing import Any

REDACTED = "***redacted***"

_SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "password",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "bearer",
}
_SENSITIVE_PATTERNS = [
    re.compile(r"(intllm_[A-Za-z0-9_\-]{6,})"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]+"),
    re.compile(r"(?i)sk-[A-Za-z0-9]{8,}"),
]


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: (REDACTED if key.lower() in _SENSITIVE_KEYS else redact(val))
            for key, val in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    if isinstance(value, str):
        result = value
        for pattern in _SENSITIVE_PATTERNS:
            result = pattern.sub(REDACTED, result)
        return result
    return value


class _RedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact(record.msg)
        if record.args:
            record.args = tuple(redact(a) for a in record.args)
        extra = getattr(record, "intllm_extra", None)
        if extra is not None:
            record.intllm_extra = redact(extra)
        return True


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extra = getattr(record, "intllm_extra", None)
        if isinstance(extra, dict):
            payload.update(extra)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(redact(payload), default=str, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())
    handler.addFilter(_RedactionFilter())
    root.addHandler(handler)
    root.setLevel(level.upper() or "INFO")

    # Uvicorn access logs are noisy and may include query strings; keep errors.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
