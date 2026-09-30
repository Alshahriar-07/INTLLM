"""Live web retrieval endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from app.core.errors import IntllmError
from app.schemas import WebFetchRequest, WebSearchResponse, WebSourceOut
from app.services.web.service import get_web_service

router = APIRouter(prefix="/web", tags=["web"])


@router.get("/status")
async def web_status() -> dict[str, object]:
    available, error = await get_web_service().health()
    return {"connected": available, "error": error}


@router.get("/search", response_model=WebSearchResponse)
async def search_web(q: str = Query(..., min_length=1)) -> WebSearchResponse:
    try:
        sources = await get_web_service().search(q)
    except IntllmError as exc:
        return WebSearchResponse(connected=False, sources=[], error=exc.message)
    return WebSearchResponse(
        connected=True,
        sources=[
            WebSourceOut(
                id=uuid.uuid4().hex,
                domain=source.domain,
                title=source.title,
                url=source.url,
                timestamp=source.timestamp,
                trustScore=source.trust_score,
                verified=source.verified,
                snippet=source.snippet,
            )
            for source in sources
        ],
    )


@router.post("/fetch")
async def fetch_page(body: WebFetchRequest) -> dict[str, object]:
    return await get_web_service().fetch(body.url)
