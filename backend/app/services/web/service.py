"""Live web retrieval.

Performs real HTTP retrieval. If the provider is unreachable or a page cannot
be fetched, the caller receives an explicit error/unavailable state - sources
are never fabricated and "verified" is only true after a real fetch.
"""

from __future__ import annotations

import html
import ipaddress
import re
import socket
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx

from app.config.settings import Settings, get_settings
from app.core.errors import ServiceUnavailableError, ValidationError
from app.core.logging import get_logger

logger = get_logger(__name__)

_TRUSTED_DOMAINS: dict[str, int] = {
    "docs.python.org": 98,
    "developer.mozilla.org": 97,
    "arxiv.org": 95,
    "github.com": 92,
    "stackoverflow.com": 88,
    "wikipedia.org": 90,
    "docs.docker.com": 95,
    "kubernetes.io": 95,
    "postgresql.org": 96,
    "learn.microsoft.com": 94,
}
_BLOCKED_HOSTS = {"localhost", "metadata.google.internal", "169.254.169.254"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class WebSource:
    title: str
    url: str
    snippet: str
    domain: str
    trust_score: int
    verified: bool = False
    timestamp: str = field(default_factory=_now_iso)


def guard_url(url: str) -> str:
    """Reject non-http(s) and internal addresses (SSRF protection)."""
    try:
        parsed = urlparse(url)
    except ValueError as exc:
        raise ValidationError(f"Invalid URL: {url}") from exc
    if parsed.scheme not in ("http", "https"):
        raise ValidationError("Only http and https URLs are permitted")
    host = (parsed.hostname or "").lower()
    if not host or host in _BLOCKED_HOSTS:
        raise ValidationError("Target host is not permitted")
    try:
        addresses = {info[4][0] for info in socket.getaddrinfo(host, None)}
    except socket.gaierror:
        # Unresolvable host: allowed but will fail at fetch time.
        return url
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValidationError("Target host resolves to a private/reserved address")
    return url


def trust_for(domain: str) -> int:
    domain = domain.lower().lstrip("www.")
    for trusted, score in _TRUSTED_DOMAINS.items():
        if domain == trusted or domain.endswith(f".{trusted}"):
            return score
    return 65


def _strip_tags(fragment: str) -> str:
    text = re.sub(r"<[^>]+>", " ", fragment)
    return html.unescape(re.sub(r"\s+", " ", text)).strip()


class WebService:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def _timeout(self) -> httpx.Timeout:
        return httpx.Timeout(self._settings.intllm_web_timeout_seconds)

    async def health(self) -> tuple[bool, str | None]:
        # A reachability probe only; never claims search works without results.
        try:
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                response = await client.get("https://duckduckgo.com/")
            return response.status_code < 500, None if response.status_code < 500 else f"HTTP {response.status_code}"
        except Exception as exc:  # noqa: BLE001
            return False, f"{type(exc).__name__}: {exc}"

    async def search(self, query: str, *, limit: int | None = None) -> list[WebSource]:
        query = query.strip()
        if not query:
            raise ValidationError("Search query must not be empty")
        limit = limit or self._settings.intllm_web_max_results
        provider = self._settings.intllm_web_provider.lower()
        if provider == "searxng":
            return await self._search_searxng(query, limit)
        return await self._search_duckduckgo(query, limit)

    async def _search_duckduckgo(self, query: str, limit: int) -> list[WebSource]:
        url = "https://html.duckduckgo.com/html/"
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout(),
                follow_redirects=True,
                headers={"User-Agent": "INTLLM/0.4.2 (+local retrieval)"},
            ) as client:
                response = await client.post(url, data={"q": query})
                response.raise_for_status()
                body = response.text
        except Exception as exc:  # noqa: BLE001
            raise ServiceUnavailableError(
                "Web search provider is unavailable", details={"reason": str(exc)}
            ) from exc

        results: list[WebSource] = []
        pattern = re.compile(
            r'<a[^>]*class="result__a"[^>]*href="(?P<href>[^"]+)"[^>]*>(?P<title>.*?)</a>'
            r'.*?<a[^>]*class="result__snippet"[^>]*>(?P<snippet>.*?)</a>',
            re.DOTALL,
        )
        for match in pattern.finditer(body):
            href = html.unescape(match.group("href"))
            href = self._unwrap_ddg_redirect(href)
            domain = (urlparse(href).hostname or "").lower()
            if not domain:
                continue
            results.append(
                WebSource(
                    title=_strip_tags(match.group("title")),
                    url=href,
                    snippet=_strip_tags(match.group("snippet")),
                    domain=domain,
                    trust_score=trust_for(domain),
                )
            )
            if len(results) >= limit:
                break
        return results

    async def _search_searxng(self, query: str, limit: int) -> list[WebSource]:
        base = self._settings.intllm_web_searxng_url.strip().rstrip("/")
        if not base:
            raise ServiceUnavailableError("SearXNG URL is not configured")
        guard_url(base)
        try:
            async with httpx.AsyncClient(timeout=self._timeout(), follow_redirects=True) as client:
                response = await client.get(
                    f"{base}/search", params={"q": query, "format": "json"}
                )
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:  # noqa: BLE001
            raise ServiceUnavailableError(
                "SearXNG provider is unavailable", details={"reason": str(exc)}
            ) from exc

        results: list[WebSource] = []
        for entry in payload.get("results", [])[:limit]:
            link = entry.get("url", "")
            domain = (urlparse(link).hostname or "").lower()
            results.append(
                WebSource(
                    title=entry.get("title", ""),
                    url=link,
                    snippet=entry.get("content", ""),
                    domain=domain,
                    trust_score=trust_for(domain),
                )
            )
        return results

    async def fetch(self, url: str) -> dict[str, Any]:
        """Fetch a page and extract readable text. Marks verified only on success."""
        guard_url(url)
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout(),
                follow_redirects=True,
                headers={"User-Agent": "INTLLM/0.4.2 (+local retrieval)"},
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                content_type = response.headers.get("content-type", "")
                body = response.text
        except Exception as exc:  # noqa: BLE001
            raise ServiceUnavailableError(
                "Web page could not be retrieved", details={"reason": str(exc)}
            ) from exc

        text = _strip_tags(body)
        return {
            "url": url,
            "domain": (urlparse(url).hostname or "").lower(),
            "content_type": content_type,
            "text": text[:8000],
            "verified": True,
            "fetched_at": _now_iso(),
        }

    @staticmethod
    def _unwrap_ddg_redirect(href: str) -> str:
        parsed = urlparse(href)
        if parsed.path.startswith("/l/") or "uddg=" in parsed.query:
            target = parse_qs(parsed.query).get("uddg")
            if target:
                return target[0]
        return href


_web: WebService | None = None


def get_web_service() -> WebService:
    global _web
    if _web is None:
        _web = WebService()
    return _web
