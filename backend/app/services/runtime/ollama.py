"""Ollama model adapter.

Talks to a real Ollama daemon over HTTP. When Ollama is unreachable the adapter
reports unavailability; it never returns invented models or completions.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.config.settings import Settings, get_settings
from app.core.logging import get_logger
from app.services.runtime.base import ChatMessage, ModelInfo, RuntimeUnavailable, StreamChunk

logger = get_logger(__name__)


class OllamaAdapter:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._base_url = self._settings.intllm_ollama_url.rstrip("/")

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self._base_url, timeout=self._settings.intllm_ollama_timeout_seconds)

    async def health(self) -> tuple[bool, str | None]:
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url, timeout=5.0
            ) as client:
                response = await client.get("/api/tags")
            if response.status_code == 200:
                return True, None
            return False, f"HTTP {response.status_code}"
        except Exception as exc:  # noqa: BLE001 - surfaced as status
            return False, f"{type(exc).__name__}: {exc}"

    async def list_models(self) -> list[ModelInfo]:
        try:
            async with self._client() as client:
                response = await client.get("/api/tags")
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            raise RuntimeUnavailable(f"Ollama model listing failed: {exc}") from exc

        models: list[ModelInfo] = []
        for entry in payload.get("models", []):
            details = entry.get("details", {}) or {}
            models.append(
                ModelInfo(
                    name=entry.get("name") or entry.get("model", ""),
                    family=details.get("family"),
                    parameter_size=details.get("parameter_size"),
                    quantization=details.get("quantization_level"),
                    size_bytes=entry.get("size"),
                    capabilities=[],
                )
            )
        return models

    async def show(self, name: str) -> dict[str, Any]:
        try:
            async with self._client() as client:
                response = await client.post("/api/show", json={"name": name})
                response.raise_for_status()
                return response.json()
        except Exception as exc:
            raise RuntimeUnavailable(f"Ollama show failed for {name}: {exc}") from exc

    async def chat(
        self,
        model: str,
        messages: list[ChatMessage],
        *,
        options: dict[str, Any] | None = None,
    ) -> AsyncIterator[StreamChunk]:
        body: dict[str, Any] = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
        }
        if options:
            body["options"] = options

        try:
            async with httpx.AsyncClient(
                base_url=self._base_url, timeout=self._settings.intllm_ollama_timeout_seconds
            ) as client, client.stream("POST", "/api/chat", json=body) as response:
                if response.status_code >= 400:
                    detail = (await response.aread()).decode("utf-8", "replace")
                    yield StreamChunk(
                        type="error",
                        error=f"Ollama returned HTTP {response.status_code}: {detail[:400]}",
                    )
                    return
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if data.get("error"):
                        yield StreamChunk(type="error", error=str(data["error"]))
                        return
                    message = data.get("message") or {}
                    content = message.get("content", "")
                    if content:
                        yield StreamChunk(type="delta", content=content, model=model)
                    if data.get("done"):
                        yield StreamChunk(
                            type="done",
                            model=model,
                            done_reason=data.get("done_reason"),
                            metrics={
                                "prompt_eval_count": data.get("prompt_eval_count"),
                                "eval_count": data.get("eval_count"),
                                "eval_duration_ns": data.get("eval_duration"),
                                "total_duration_ns": data.get("total_duration"),
                            },
                        )
                        return
        except httpx.TimeoutException as exc:
            yield StreamChunk(type="error", error=f"Ollama request timed out: {exc}")
        except Exception as exc:  # noqa: BLE001
            yield StreamChunk(type="error", error=f"Ollama unavailable: {exc}")

    async def embeddings(self, model: str, text: str) -> list[float] | None:
        if not model:
            return None
        try:
            async with self._client() as client:
                response = await client.post(
                    "/api/embeddings", json={"model": model, "prompt": text}
                )
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "embedding request failed",
                extra={"intllm_extra": {"model": model, "error": str(exc)}},
            )
            return None
        embedding = payload.get("embedding")
        return [float(v) for v in embedding] if embedding else None

    async def pull(self, name: str) -> AsyncIterator[dict[str, Any]]:
        try:
            async with httpx.AsyncClient(base_url=self._base_url, timeout=None) as client:
                async with client.stream("POST", "/api/pull", json={"name": name, "stream": True}) as response:
                    if response.status_code >= 400:
                        detail = (await response.aread()).decode("utf-8", "replace")
                        yield {"status": "error", "error": f"HTTP {response.status_code}: {detail[:300]}"}
                        return
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            yield json.loads(line)
                        except json.JSONDecodeError:
                            continue
        except Exception as exc:  # noqa: BLE001
            yield {"status": "error", "error": f"Ollama unavailable: {exc}"}

    async def delete(self, name: str) -> tuple[bool, str | None]:
        try:
            async with self._client() as client:
                response = await client.request(
                    "DELETE", "/api/delete", json={"name": name}
                )
            if response.status_code >= 400:
                return False, f"HTTP {response.status_code}"
            return True, None
        except Exception as exc:  # noqa: BLE001
            return False, f"{type(exc).__name__}: {exc}"


_adapter: OllamaAdapter | None = None


def get_ollama_adapter() -> OllamaAdapter:
    global _adapter
    if _adapter is None:
        _adapter = OllamaAdapter()
    return _adapter
