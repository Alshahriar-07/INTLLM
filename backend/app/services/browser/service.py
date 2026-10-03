"""Browser agent service.

Wraps Playwright behind a dedicated service. When Playwright (or its browser
binaries) are not installed, operations return an explicit unavailable error
rather than pretending a session exists. Never silently performs sensitive
actions; those are gated by the tool gateway's approval policy.
"""

from __future__ import annotations

import base64
from datetime import UTC, datetime
from typing import Any

from app.config.settings import get_settings
from app.core.errors import ServiceUnavailableError
from app.core.logging import get_logger

logger = get_logger(__name__)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class BrowserService:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._playwright = None
        self._browser = None
        self._page = None
        self._screenshot: str | None = None
        self._last_error: str | None = None

    # --- availability -----------------------------------------------------
    def _import_playwright(self):
        try:
            from playwright.async_api import async_playwright
        except Exception as exc:  # noqa: BLE001
            self._last_error = f"Playwright is not installed: {exc}"
            return None
        return async_playwright

    def availability(self) -> tuple[bool, str | None]:
        if not self._settings.intllm_browser_enabled:
            return False, "Browser agent is disabled in configuration"
        if self._import_playwright() is None:
            return False, self._last_error or "Playwright is not installed"
        return True, None

    @property
    def is_active(self) -> bool:
        return self._page is not None

    async def _ensure_page(self):
        if self._page is not None:
            return self._page
        factory = self._import_playwright()
        if factory is None:
            raise ServiceUnavailableError(self._last_error or "Playwright is unavailable")
        try:
            self._playwright = await factory().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self._settings.intllm_browser_headless
            )
            self._page = await self._browser.new_page()
        except Exception as exc:
            raise ServiceUnavailableError(
                "Browser could not be launched (browsers may need `playwright install`)",
                details={"reason": str(exc)},
            ) from exc
        return self._page

    async def state(self) -> dict[str, Any]:
        available, error = self.availability()
        tabs: list[dict[str, Any]] = []
        if self._page is not None:
            tabs.append(
                {
                    "id": "active",
                    "title": await self._safe_title(),
                    "url": self._page.url,
                    "active": True,
                    "favicon": None,
                }
            )
        return {
            "connected": available,
            "active": self.is_active,
            "tabs": tabs,
            "screenshot": self._screenshot,
            "error": error,
        }

    async def _safe_title(self) -> str:
        try:
            return await self._page.title()
        except Exception:  # noqa: BLE001
            return "Untitled"

    async def open(self, url: str) -> dict[str, Any]:
        from app.services.web.service import guard_url

        guard_url(url)
        page = await self._ensure_page()
        await page.goto(url, timeout=self._settings.intllm_browser_timeout_seconds * 1000)
        return {"url": page.url, "title": await self._safe_title(), "opened_at": _now_iso()}

    async def read(self, url: str) -> dict[str, Any]:
        page = await self._ensure_page()
        if url and page.url != url:
            await self.open(url)
        text = await page.inner_text("body")
        return {"url": page.url, "text": text[:20000], "captured_at": _now_iso()}

    async def click(self, selector: str) -> dict[str, Any]:
        page = await self._ensure_page()
        await page.click(selector, timeout=self._settings.intllm_browser_timeout_seconds * 1000)
        return {"selector": selector, "url": page.url, "clicked_at": _now_iso()}

    async def screenshot(self) -> dict[str, Any]:
        page = await self._ensure_page()
        raw = await page.screenshot()
        self._screenshot = base64.b64encode(raw).decode("ascii")
        return {"format": "png", "encoding": "base64", "captured_at": _now_iso()}

    async def close(self) -> None:
        try:
            if self._browser is not None:
                await self._browser.close()
            if self._playwright is not None:
                await self._playwright.stop()
        except Exception:  # noqa: BLE001
            logger.warning("browser shutdown encountered an error")
        finally:
            self._page = None
            self._browser = None
            self._playwright = None


_browser: BrowserService | None = None


def get_browser_service() -> BrowserService:
    global _browser
    if _browser is None:
        _browser = BrowserService()
    return _browser
