/**
 * INTLLM frontend API client.
 *
 * Central transport boundary. Components never call `fetch` directly; they use
 * the service modules in `src/lib/services`, which use this client.
 *
 * Endpoint configuration comes from Vite environment variables:
 *   VITE_INTLLM_BASE_URL  (preferred, e.g. http://127.0.0.1:8000)
 *   VITE_INTLLM_HOST / VITE_INTLLM_PORT  (fallback)
 *
 * NOTE: the supplied runtime port 240426 is NOT a valid TCP port and must never
 * be used to build a URL. It is documented in `.env.example` only.
 */

const env = (import.meta as any).env ?? {};

export const INTLLM_HOST: string = env.VITE_INTLLM_HOST || '127.0.0.1';
export const INTLLM_PORT: string = env.VITE_INTLLM_PORT || '8000';

/** Validated base URL, or `null` when the configured port is out of range. */
function resolveBaseUrl(): string | null {
  const explicit: string | undefined = env.VITE_INTLLM_BASE_URL;
  if (explicit) return explicit.replace(/\/+$/, '');

  const port = Number(INTLLM_PORT);
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    // Invalid port (e.g. the supplied 240426): do not fabricate a URL.
    return null;
  }
  return `http://${INTLLM_HOST}:${port}`;
}

export const INTLLM_BASE_URL: string | null = resolveBaseUrl();
export const API_BASE: string | null = INTLLM_BASE_URL ? `${INTLLM_BASE_URL}/api` : null;
export const OPENAI_BASE: string | null = INTLLM_BASE_URL ? `${INTLLM_BASE_URL}/v1` : null;

const DEFAULT_TIMEOUT_MS = 15000;

/** Ollama daemon endpoint as configured on the backend (read-only display). */
export const OLLAMA_DEFAULT_URL = 'http://127.0.0.1:11434';

/** Configured polling interval override (ms); default 8s, clamped 5–60s. */
export const POLLING_INTERVAL_MS: number = (() => {
  const raw = Number(env.VITE_INTLLM_POLLING_INTERVAL_MS);
  if (!Number.isFinite(raw) || raw <= 0) return 8000;
  return Math.min(60000, Math.max(5000, raw));
})();

/** Connection timeout override (ms). */
export const CONNECTION_TIMEOUT_MS: number = (() => {
  const raw = Number(env.VITE_INTLLM_CONNECTION_TIMEOUT_MS);
  if (!Number.isFinite(raw) || raw <= 0) return DEFAULT_TIMEOUT_MS;
  return Math.min(60000, Math.max(2000, raw));
})();

/** True when a usable backend endpoint is configured. */
export const isEndpointConfigured = (): boolean => API_BASE !== null;

export interface ApiResult<T> {
  ok: boolean;
  status: number;
  data?: T;
  /** Human-readable error; never a raw stack trace. */
  error?: string;
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
  timeoutMs: number = DEFAULT_TIMEOUT_MS,
  acceptStatuses: number[] = []
): Promise<ApiResult<T>> {
  if (!API_BASE) {
    return {
      ok: false,
      status: 0,
      error: 'INTLLM endpoint is not configured (invalid or missing port)'
    };
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...init,
      signal: controller.signal,
      headers: {
        Accept: 'application/json',
        ...(init.body ? { 'Content-Type': 'application/json' } : {}),
        ...(init.headers || {})
      }
    });

    const text = await response.text();
    const payload = text ? safeJson(text) : undefined;

    if (!response.ok && !acceptStatuses.includes(response.status)) {
      const message =
        payload?.error?.message || payload?.detail || `Request failed (HTTP ${response.status})`;
      return { ok: false, status: response.status, error: String(message) };
    }
    return { ok: true, status: response.status, data: payload as T };
  } catch (error: any) {
    const message =
      error?.name === 'AbortError'
        ? 'Request timed out'
        : 'INTLLM runtime is not reachable';
    return { ok: false, status: 0, error: message };
  } finally {
    clearTimeout(timer);
  }
}

function safeJson(text: string): any {
  try {
    return JSON.parse(text);
  } catch {
    return undefined;
  }
}

export interface HealthServices {
  intllm?: { status: string; detail?: string | null };
  postgres?: { status: string; detail?: string | null };
  ollama?: { status: string; detail?: string | null };
  [key: string]: { status: string; detail?: string | null } | undefined;
}

export interface HealthSnapshot {
  connected: boolean;
  status: 'ok' | 'degraded' | 'offline';
  version?: string;
  environment?: string;
  services: HealthServices;
  error?: string;
}

export async function probeHealth(): Promise<HealthSnapshot> {
  const result = await apiRequest<{
    status: 'ok' | 'degraded';
    version: string;
    environment: string;
    services: HealthServices;
  }>('/health', { method: 'GET' }, 4000, [503]);

  if (!result.ok || !result.data) {
    return { connected: false, status: 'offline', services: {}, error: result.error };
  }
  return {
    connected: true,
    status: result.data.status,
    version: result.data.version,
    environment: result.data.environment,
    services: result.data.services
  };
}

export interface SseHandlers {
  onEvent: (type: string, data: any) => void;
  onError?: (message: string) => void;
  onClose?: () => void;
}

/**
 * Consume an SSE endpoint via fetch streaming. Returns a cleanup function that
 * aborts the request (used for stop-generation).
 */
export function openEventStream(
  path: string,
  body: unknown,
  handlers: SseHandlers,
  method: 'POST' | 'GET' = 'POST'
): () => void {
  const controller = new AbortController();

  (async () => {
    if (!API_BASE) {
      handlers.onError?.('INTLLM endpoint is not configured');
      return;
    }
    try {
      const response = await fetch(`${API_BASE}${path}`, {
        method,
        signal: controller.signal,
        headers: {
          Accept: 'text/event-stream',
          ...(body ? { 'Content-Type': 'application/json' } : {})
        },
        body: body ? JSON.stringify(body) : undefined
      });

      if (!response.ok || !response.body) {
        handlers.onError?.(`Stream failed (HTTP ${response.status})`);
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let boundary = buffer.indexOf('\n\n');
        while (boundary !== -1) {
          const frame = buffer.slice(0, boundary);
          buffer = buffer.slice(boundary + 2);
          dispatchFrame(frame, handlers);
          boundary = buffer.indexOf('\n\n');
        }
      }
      handlers.onClose?.();
    } catch (error: any) {
      if (error?.name !== 'AbortError') {
        handlers.onError?.('INTLLM runtime is not reachable');
      }
    }
  })();

  return () => controller.abort();
}

function dispatchFrame(frame: string, handlers: SseHandlers) {
  let eventType = 'message';
  const dataLines: string[] = [];
  for (const line of frame.split('\n')) {
    if (line.startsWith('event:')) eventType = line.slice(6).trim();
    else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim());
  }
  if (!dataLines.length) return;
  const raw = dataLines.join('\n');
  try {
    handlers.onEvent(eventType, JSON.parse(raw));
  } catch {
    handlers.onEvent(eventType, raw);
  }
}
