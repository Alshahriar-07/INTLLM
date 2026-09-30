"""Provider-agnostic model runtime contract.

Ollama is the first implementation; future runtimes only need to satisfy this
interface, keeping provider-specific code behind an adapter boundary.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from app.core.errors import ServiceUnavailableError


class RuntimeUnavailable(ServiceUnavailableError):
    """Raised when the model runtime (e.g. Ollama) cannot be reached."""

    def __init__(self, message: str = "Model runtime is unavailable") -> None:
        super().__init__(message)


@dataclass(slots=True)
class ModelInfo:
    name: str
    family: str | None = None
    parameter_size: str | None = None
    quantization: str | None = None
    context_length: int | None = None
    size_bytes: int | None = None
    capabilities: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ChatMessage:
    role: str
    content: str


@dataclass(slots=True)
class StreamChunk:
    type: str  # "delta" | "done" | "error"
    content: str = ""
    model: str | None = None
    done_reason: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@runtime_checkable
class ModelRuntime(Protocol):
    async def health(self) -> tuple[bool, str | None]: ...

    async def list_models(self) -> list[ModelInfo]: ...

    async def chat(
        self, model: str, messages: list[ChatMessage], *, options: dict[str, Any] | None = None
    ) -> AsyncIterator[StreamChunk]: ...

    async def embeddings(self, model: str, text: str) -> list[float] | None: ...
