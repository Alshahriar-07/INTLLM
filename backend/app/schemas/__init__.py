"""Pydantic request/response schemas.

Field names mirror the frontend TypeScript interfaces so the service boundary
can be wired without UI refactoring.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# --- Health / status -------------------------------------------------------
class ServiceState(BaseModel):
    status: Literal["connected", "offline", "unavailable", "degraded"]
    detail: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    environment: str
    services: dict[str, ServiceState]


# --- Models ----------------------------------------------------------------
class ModelOut(BaseModel):
    id: str
    name: str
    parameterSize: str | None = None
    quantization: str | None = None
    contextWindow: str | None = None
    memoryReqGB: float | None = None
    tier: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    installed: bool = False
    isDefault: bool = False
    downloadProgress: float | None = None
    family: str | None = None


class ModelListResponse(BaseModel):
    connected: bool
    models: list[ModelOut] = Field(default_factory=list)
    error: str | None = None


class ModelPullRequest(BaseModel):
    name: str


class ModelRecommendation(BaseModel):
    name: str
    tier: str | None = None
    memory_req_gb: float | None = None
    fits: bool
    utilization_percent: float | None = None
    installed: bool
    parameter_size: str | None = None
    family: str | None = None


class ModelRecommendResponse(BaseModel):
    vram_total_gb: float | None = None
    ram_total_gb: float | None = None
    recommendations: list[ModelRecommendation] = Field(default_factory=list)


# --- Chat ------------------------------------------------------------------
class ChatMessageIn(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatRequestBody(BaseModel):
    messages: list[ChatMessageIn]
    model: str | None = None
    conversation_id: uuid.UUID | None = None
    use_brain: bool = True
    use_web: bool = False
    # "agent" activates the workspace-aware coding assistant behaviour.
    mode: Literal["chat", "agent"] = "chat"
    workspace: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)


class OpenAIChatRequest(BaseModel):
    """OpenAI-compatible chat completion request.

    Uses the field names real OpenAI clients send (``stream`` at the top level).
    Unknown fields (e.g. ``frequency_penalty``) are accepted and ignored so
    clients with extra parameters still work. INTLLM-specific toggles are read
    from ``extra_body`` (``intllm_use_web`` / ``intllm_use_brain``).
    """

    model_config = ConfigDict(extra="allow")

    model: str | None = None
    messages: list[ChatMessageIn]
    stream: bool = False
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    stop: str | list[str] | None = None


class ActivityStep(BaseModel):
    id: str
    type: str
    label: str
    status: str
    latencyMs: int | None = None
    detail: str | None = None
    metadata: dict[str, Any] | None = None


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    timestamp: str
    model: str | None = None
    activities: list[dict[str, Any]] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    memoryUsed: int = 0


class ConversationOut(BaseModel):
    id: str
    title: str
    model: str | None = None
    createdAt: str
    updatedAt: str


class ConversationDetailOut(ConversationOut):
    messages: list[MessageOut] = Field(default_factory=list)


class ConversationCreate(BaseModel):
    title: str | None = None
    model: str | None = None


class ConversationUpdate(BaseModel):
    title: str


# --- Brain / memory --------------------------------------------------------
class MemoryOut(BaseModel):
    id: str
    title: str
    layer: str
    type: str
    confidence: float
    freshnessScore: float
    source: str
    lastVerified: str
    status: str
    keywords: list[str] = Field(default_factory=list)
    rawSnippet: str
    vectorId: str


class BrainStatsOut(BaseModel):
    totalMemories: int
    hitRatePercent: float | None = None
    avgLookupTimeMs: float | None = None
    freshnessPercent: float | None = None
    byLayer: dict[str, int] = Field(default_factory=dict)


class BrainSearchResponse(BaseModel):
    connected: bool
    memories: list[MemoryOut] = Field(default_factory=list)
    stats: BrainStatsOut | None = None
    error: str | None = None


class MemoryCreateRequest(BaseModel):
    title: str
    content: str
    type: Literal["fact", "workflow", "lesson", "preference"] = "fact"
    confidence: float = 60.0
    importance: float = 50.0
    freshness_policy: Literal["static", "long", "medium", "short", "live"] = "medium"
    keywords: list[str] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)


# --- Web -------------------------------------------------------------------
class WebSourceOut(BaseModel):
    id: str
    domain: str
    title: str
    url: str
    timestamp: str
    trustScore: int
    verified: bool
    snippet: str


class WebSearchResponse(BaseModel):
    connected: bool
    sources: list[WebSourceOut] = Field(default_factory=list)
    error: str | None = None


class WebFetchRequest(BaseModel):
    url: str


# --- Tools -----------------------------------------------------------------
class ToolOut(BaseModel):
    id: str
    name: str
    category: str
    description: str
    permissionLevel: str
    enabled: bool
    riskScore: str


class ToolListResponse(BaseModel):
    connected: bool
    tools: list[ToolOut] = Field(default_factory=list)
    error: str | None = None


class ToolRunRequest(BaseModel):
    arguments: dict[str, Any] = Field(default_factory=dict)
    decision: Literal["allow", "allow_session", "deny"] | None = None


class ToolRunResponse(BaseModel):
    tool: str
    status: str
    output: dict[str, Any] | None = None
    error: str | None = None
    duration_ms: float = 0.0
    permission: str | None = None


# --- Browser ---------------------------------------------------------------
class BrowserTabOut(BaseModel):
    id: str
    title: str
    url: str
    active: bool
    favicon: str | None = None


class BrowserStateResponse(BaseModel):
    connected: bool
    active: bool = False
    tabs: list[BrowserTabOut] = Field(default_factory=list)
    screenshot: str | None = None
    error: str | None = None


class BrowserActionRequest(BaseModel):
    action: Literal["open", "read", "click", "screenshot"]
    url: str | None = None
    selector: str | None = None
    decision: Literal["allow", "allow_session", "deny"] | None = None


# --- API keys --------------------------------------------------------------
class ApiKeyOut(BaseModel):
    id: str
    name: str
    key: str
    created: str
    lastUsed: str | None = None
    scopes: list[str] = Field(default_factory=list)
    status: str


class ApiKeysResponse(BaseModel):
    connected: bool
    keys: list[ApiKeyOut] = Field(default_factory=list)
    baseUrl: str
    error: str | None = None


class ApiKeyCreateRequest(BaseModel):
    name: str
    scopes: list[str] = Field(default_factory=list)


class ApiKeyCreatedResponse(BaseModel):
    key: ApiKeyOut
    secret: str  # shown exactly once


# --- System ----------------------------------------------------------------
class SystemStatusResponse(BaseModel):
    connected: bool
    cpu: dict[str, Any] | None = None
    ram: dict[str, Any] | None = None
    gpu: dict[str, Any] | None = None
    disk: dict[str, Any] | None = None
    os: dict[str, Any] | None = None
    services: dict[str, Any] = Field(default_factory=dict)
    capturedAt: str
    error: str | None = None


# --- Background ------------------------------------------------------------
class BackgroundTaskOut(BaseModel):
    id: str
    name: str
    type: str
    priority: str
    status: str
    progress: float
    currentAction: str
    cpuBudget: str
    createdAt: str | None = None


class BackgroundStatusResponse(BaseModel):
    connected: bool
    tasks: list[BackgroundTaskOut] = Field(default_factory=list)
    isThrottled: bool = False
    paused: bool = False
    state: str = "NORMAL"
    recentLatencyMs: float | None = None
    error: str | None = None


# --- Ollama control --------------------------------------------------------
class OllamaLoadedModel(BaseModel):
    name: str | None = None
    sizeBytes: int | None = None
    vramBytes: int | None = None
    expiresAt: str | None = None


class OllamaMemory(BaseModel):
    loadedModels: int = 0
    vramUsedBytes: int = 0


class OllamaStatusResponse(BaseModel):
    status: Literal["running", "stopped", "starting", "stopping", "unavailable", "error"]
    endpoint: str
    version: str | None = None
    modelCount: int | None = None
    loadedModels: list[OllamaLoadedModel] = Field(default_factory=list)
    memory: OllamaMemory | None = None
    reason: str | None = None
    lastChecked: str


class OllamaActionResponse(BaseModel):
    ok: bool
    operation: str
    status: Literal["running", "stopped", "starting", "stopping", "unavailable", "error"]
    changed: bool = False
    running: bool = False
    startedVia: str | None = None
    message: str | None = None
    error: str | None = None


# --- Agent mode / workspace ------------------------------------------------
class AgentWorkspaceRequest(BaseModel):
    path: str


class AgentWorkspaceOut(BaseModel):
    configured: bool
    path: str | None = None
    exists: bool = False
    writable: bool = False
    fileCount: int | None = None
    sessionGrants: list[str] = Field(default_factory=list)
    terminalEnabled: bool = True


class AgentFsEntryOut(BaseModel):
    name: str
    path: str
    isDir: bool
    size: int | None = None


class AgentOperationOut(BaseModel):
    operation: str
    status: str
    output: dict[str, Any] | None = None
    error: str | None = None
    target: str | None = None
    risk: str = "Low"
    durationMs: float = 0.0
    permission: str = "read-only"


class AgentWriteRequest(BaseModel):
    path: str
    content: str = ""
    decision: Literal["allow", "allow_session", "deny"] | None = None


class AgentCreateDirRequest(BaseModel):
    path: str
    decision: Literal["allow", "allow_session", "deny"] | None = None


class AgentDeleteRequest(BaseModel):
    path: str
    decision: Literal["allow", "allow_session", "deny"] | None = None


class AgentMoveRequest(BaseModel):
    source: str
    destination: str
    decision: Literal["allow", "allow_session", "deny"] | None = None


class AgentTerminalRequest(BaseModel):
    command: str
    cwd: str | None = None
    decision: Literal["allow", "allow_session", "deny"] | None = None


class AgentPermissionRequest(BaseModel):
    operation: str
    decision: Literal["allow_session", "revoke"]


# --- Diagnostics -----------------------------------------------------------
class DiagnosticsResponse(BaseModel):
    metrics: dict[str, Any]
    runtime_endpoint: dict[str, Any]
    environment: str
    audit: list[dict[str, Any]] = Field(default_factory=list)
    capturedAt: datetime
