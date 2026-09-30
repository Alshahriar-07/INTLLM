"""Playwright-backed browser agent service."""

from app.services.browser.service import BrowserService, get_browser_service

__all__ = ["BrowserService", "get_browser_service"]
