"""OpenAI-compatible local API.

Requests route through the same INTLLM orchestrator (memory/security aware)
rather than bypassing it. Requires an API key unless bootstrapping from
loopback before any key exists.

Implemented (and tested) endpoints:

* ``GET  /v1/models``          list installed models
* ``GET  /v1/models/{model}``  retrieve one model
* ``POST /v1/chat/completions`` chat, with ``stream: true`` SSE support

Additional OpenAI endpoints are intentionally not exposed until implemented.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_session_optional, require_api_key
from app.api.sse import SSE_HEADERS
from app.core.errors import NotFoundError, ServiceUnavailableError
from app.schemas import OpenAIChatRequest
from app.services.chat.service import ChatRequest, get_chat_service
from app.services.models.service import ModelService
from app.services.runtime.base import ChatMessage, RuntimeUnavailable

router = APIRouter(prefix="/v1", tags=["openai"])
_model_service = ModelService()


def _sse(payload: dict[str, Any]) -> str:
    """Serialize one SSE frame. ``data:`` lines always end with a blank line."""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _installed_names(records: list[Any]) -> list[str]:
    return [record.name for record in records if record.installed]


async def _list_installed(session) -> list[str]:
    if session is not None:
        return _installed_names(await _model_service.sync_registry(session))
    live = await _model_service._adapter.list_models()
    return [info.name for info in live]


def _usage_from_metrics(metrics: dict[str, Any]) -> dict[str, int]:
    """Map Ollama counters onto the OpenAI ``usage`` shape."""
    prompt = int(metrics.get("prompt_eval_count") or 0)
    completion = int(metrics.get("eval_count") or 0)
    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": prompt + completion,
    }


def _error_frame(message: str, error_type: str) -> str:
    return _sse({"error": {"message": message, "type": error_type}})


@router.get("/models")
async def list_models(
    _key=Depends(require_api_key),
    session=Depends(get_session_optional),
) -> dict[str, object]:
    names = await _list_installed(session)
    created = int(time.time())
    return {
        "object": "list",
        "data": [
            {"id": name, "object": "model", "created": created, "owned_by": "intllm"}
            for name in names
        ],
    }


@router.get("/models/{model_id:path}")
async def get_model(
    model_id: str,
    _key=Depends(require_api_key),
    session=Depends(get_session_optional),
) -> dict[str, object]:
    """Retrieve a single model, mirroring ``GET /v1/models/{model}``."""
    names = await _list_installed(session)
    if model_id not in names:
        raise NotFoundError(f"Model not found: {model_id}")
    return {
        "id": model_id,
        "object": "model",
        "created": int(time.time()),
        "owned_by": "intllm",
    }


def _to_chat_request(body: OpenAIChatRequest) -> ChatRequest:
    """Translate an OpenAI request into the INTLLM orchestrator request."""
    extra = body.model_extra or {}
    options: dict[str, Any] = {}
    if body.temperature is not None:
        options["temperature"] = body.temperature
    if body.top_p is not None:
        options["top_p"] = body.top_p
    if body.max_tokens is not None:
        options["num_predict"] = body.max_tokens
    if body.stop is not None:
        options["stop"] = body.stop

    return ChatRequest(
        messages=[ChatMessage(role=m.role, content=m.content) for m in body.messages],
        model=body.model,
        use_brain=bool(extra.get("intllm_use_brain", True)),
        use_web=bool(extra.get("intllm_use_web", False)),
        options=options,
    )


@router.post("/chat/completions")
async def chat_completions(
    body: OpenAIChatRequest,
    _key=Depends(require_api_key),
):
    request = _to_chat_request(body)

    if not body.stream:
        try:
            model, result, _sources = await get_chat_service().complete(request)
        except RuntimeUnavailable as exc:
            raise ServiceUnavailableError(str(exc)) from exc
        metrics = result.get("metrics", {})
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": result["content"]},
                    "finish_reason": metrics.get("done_reason") or "stop",
                }
            ],
            "usage": _usage_from_metrics(metrics),
        }

    completion_id = f"chatcmpl-{uuid.uuid4().hex}"

    async def generator():
        try:
            model = await get_chat_service().resolve_model(body.model)
        except RuntimeUnavailable as exc:
            yield _error_frame(str(exc), "service_unavailable")
            yield _sse_done()
            return

        # First chunk announces the assistant role, as OpenAI does.
        yield _sse(
            {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model,
                "choices": [
                    {"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}
                ],
            }
        )

        async for event in get_chat_service().stream(request):
            event_type = event["type"]
            if event_type == "assistant.delta":
                chunk = {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": event["data"]["content"]},
                            "finish_reason": None,
                        }
                    ],
                }
                yield _sse(chunk)
            elif event_type == "assistant.completed":
                chunk = {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                }
                yield _sse(chunk)
            elif event_type == "chat.error":
                data = event.get("data") or {}
                message = data.get("message") if isinstance(data, dict) else str(data)
                yield _error_frame(message or "generation failed", "internal_error")

        yield _sse_done()

    return StreamingResponse(
        generator(), media_type="text/event-stream", headers=SSE_HEADERS
    )


def _sse_done() -> str:
    return "data: [DONE]\n\n"
