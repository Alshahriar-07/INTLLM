"""Model runtime adapters (Ollama first)."""

from app.services.runtime.base import (
    ChatMessage,
    ModelInfo,
    ModelRuntime,
    RuntimeUnavailable,
    StreamChunk,
)
from app.services.runtime.ollama import OllamaAdapter, get_ollama_adapter

__all__ = [
    "ChatMessage",
    "ModelInfo",
    "ModelRuntime",
    "OllamaAdapter",
    "RuntimeUnavailable",
    "StreamChunk",
    "get_ollama_adapter",
]
