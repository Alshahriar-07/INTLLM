"""Ollama runtime control routes.

Delegates all process management to ``app.services.ollama``; handlers only
translate service results into HTTP responses.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.schemas import OllamaActionResponse, OllamaStatusResponse
from app.services.ollama.service import get_ollama_control_service

router = APIRouter(prefix="/ollama", tags=["ollama"])


@router.get("/status", response_model=OllamaStatusResponse)
async def status() -> OllamaStatusResponse:
    return OllamaStatusResponse(**await get_ollama_control_service().describe())


async def _perform(operation: str) -> dict[str, Any]:
    return await getattr(get_ollama_control_service(), operation)()


@router.post("/start", response_model=OllamaActionResponse)
async def start() -> OllamaActionResponse:
    return OllamaActionResponse(operation="start", **await _perform("start"))


@router.post("/stop", response_model=OllamaActionResponse)
async def stop() -> OllamaActionResponse:
    return OllamaActionResponse(operation="stop", **await _perform("stop"))


@router.post("/restart", response_model=OllamaActionResponse)
async def restart() -> OllamaActionResponse:
    return OllamaActionResponse(operation="restart", **await _perform("restart"))
