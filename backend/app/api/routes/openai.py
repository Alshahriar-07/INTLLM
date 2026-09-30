"""OpenAI-compatible local API.

Requests route through the same INTLLM orchestrator (memory/security aware)
rather than bypassing it. Requires an API key unless bootstrapping from
loopback before any key exists.
"""

from __future__ import annotations

import json
import time
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_session_optional, require_api_key
from app.api.sse import SSE_HEADERS
from app.core.errors import ServiceUnavailableError
from app.schemas import ChatRequestBody
from app.services.chat.service import ChatRequest, get_chat_service
from app.services.models.service import ModelService
from app.services.runtime.base import ChatMessage, RuntimeUnavailable

router = APIRouter(prefix="/v1", tags=["openai"])
_model_service = ModelService()


@router.get("/models")
async def list_models(
    _key=Depends(require_api_key),
    session=Depends(get_session_optional),
) -> dict[str, object]:
    if session is not None:
        records = await _model_service.sync_registry(session)
        names = [r.name for r in records if r.installed]
    else:
        live = await _model_service._adapter.list_models()
        names = [info.name for info in live]
    created = int(time.time())
    return {
        "object": "list",
        "data": [
            {"id": name, "object": "model", "created": created, "owned_by": "intllm"}
            for name in names
        ],
    }


@router.post("/chat/completions")
async def chat_completions(
    body: ChatRequestBody,
    _key=Depends(require_api_key),
):
    stream = bool(body.options.get("stream", False))
    request = ChatRequest(
        messages=[ChatMessage(role=m.role, content=m.content) for m in body.messages],
        model=body.model,
        use_brain=body.use_brain,
        use_web=body.use_web,
        options={k: v for k, v in body.options.items() if k != "stream"},
    )

    if not stream:
        try:
            model, result, _sources = await get_chat_service().complete(request)
        except RuntimeUnavailable as exc:
            raise ServiceUnavailableError(str(exc)) from exc
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": result["content"]},
                    "finish_reason": "stop",
                }
            ],
            "usage": result.get("metrics", {}),
        }

    completion_id = f"chatcmpl-{uuid.uuid4().hex}"

    async def generator():
        try:
            model = await get_chat_service().resolve_model(body.model)
        except RuntimeUnavailable as exc:
            yield f"data: {json.dumps({'error': {'message': str(exc), 'type': 'service_unavailable'}})}\n\n"
            yield "data: [DONE]\n\n"
            return

        async for event in get_chat_service().stream(request):
            if event["type"] == "assistant.delta":
                chunk = {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [
                        {"index": 0, "delta": {"content": event["data"]["content"]}, "finish_reason": None}
                    ],
                }
                yield f"data: {json.dumps(chunk)}\n\n"
            elif event["type"] == "assistant.completed":
                chunk = {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                }
                yield f"data: {json.dumps(chunk)}\n\n"
            elif event["type"] == "chat.error":
                yield f"data: {json.dumps({'error': event['data']})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generator(), media_type="text/event-stream", headers=SSE_HEADERS)
