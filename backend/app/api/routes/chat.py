"""Chat endpoints (SSE streaming + non-streaming completion)."""

from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.sse import SSE_HEADERS
from app.schemas import ChatRequestBody
from app.services.chat.service import ChatRequest, get_chat_service
from app.services.runtime.base import ChatMessage, RuntimeUnavailable

router = APIRouter(prefix="/chat", tags=["chat"])


def _to_request(body: ChatRequestBody) -> ChatRequest:
    return ChatRequest(
        messages=[ChatMessage(role=m.role, content=m.content) for m in body.messages],
        model=body.model,
        conversation_id=body.conversation_id,
        use_brain=body.use_brain,
        use_web=body.use_web,
        options=body.options,
    )


@router.post("/stream")
async def stream_chat(body: ChatRequestBody) -> StreamingResponse:
    chat = get_chat_service()

    async def generator():
        async for event in chat.stream(_to_request(body)):
            event_type = event["type"]
            yield f"event: {event_type}\ndata: {json.dumps(event['data'], default=str)}\n\n"

    return StreamingResponse(generator(), media_type="text/event-stream", headers=SSE_HEADERS)


@router.post("/completions")
async def complete_chat(body: ChatRequestBody) -> dict[str, object]:
    try:
        model, result, sources = await get_chat_service().complete(_to_request(body))
    except RuntimeUnavailable as exc:
        return {"error": {"message": str(exc), "type": "service_unavailable"}}
    return {
        "model": model,
        "content": result["content"],
        "metrics": result["metrics"],
        "sources": sources,
    }
