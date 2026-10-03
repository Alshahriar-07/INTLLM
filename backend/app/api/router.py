"""Internal API router assembly (mounted under the configured prefix)."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import (
    agent,
    api_keys,
    api_server,
    background,
    brain,
    browser,
    chat,
    conversations,
    diagnostics,
    health,
    models,
    ollama,
    system,
    tools,
    web,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(agent.router)
api_router.include_router(system.router)
api_router.include_router(models.router)
api_router.include_router(ollama.router)
api_router.include_router(chat.router)
api_router.include_router(conversations.router)
api_router.include_router(brain.router)
api_router.include_router(web.router)
api_router.include_router(tools.router)
api_router.include_router(browser.router)
api_router.include_router(api_keys.router)
api_router.include_router(api_server.router)
api_router.include_router(background.router)
api_router.include_router(diagnostics.router)
