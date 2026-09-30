import { apiRequest } from '../api/client';

export type OllamaRuntimeState =
  | 'running'
  | 'stopped'
  | 'starting'
  | 'stopping'
  | 'unavailable'
  | 'error';

export interface OllamaLoadedModel {
  name?: string | null;
  sizeBytes?: number | null;
  vramBytes?: number | null;
  expiresAt?: string | null;
}

export interface OllamaStatus {
  status: OllamaRuntimeState;
  endpoint: string;
  version: string | null;
  modelCount: number | null;
  loadedModels: OllamaLoadedModel[];
  memory: { loadedModels: number; vramUsedBytes: number } | null;
  reason: string | null;
  lastChecked: string;
}

export interface OllamaActionResult {
  ok: boolean;
  operation: 'start' | 'stop' | 'restart';
  status: OllamaRuntimeState;
  changed?: boolean;
  running?: boolean;
  startedVia?: string | null;
  message?: string | null;
  error?: string | null;
}

export const ollamaService = {
  async getStatus(): Promise<OllamaStatus | null> {
    const result = await apiRequest<OllamaStatus>('/ollama/status');
    return result.ok ? (result.data ?? null) : null;
  },

  async getStatusOrError(): Promise<{ status: OllamaStatus | null; error?: string }> {
    const result = await apiRequest<OllamaStatus>('/ollama/status');
    if (!result.ok) {
      return { status: null, error: result.error };
    }
    return { status: result.data ?? null };
  },

  async start(): Promise<OllamaActionResult | null> {
    const result = await apiRequest<OllamaActionResult>('/ollama/start', { method: 'POST' }, 60000);
    return result.data ?? null;
  },

  async stop(): Promise<OllamaActionResult | null> {
    const result = await apiRequest<OllamaActionResult>('/ollama/stop', { method: 'POST' }, 60000);
    return result.data ?? null;
  },

  async restart(): Promise<OllamaActionResult | null> {
    const result = await apiRequest<OllamaActionResult>('/ollama/restart', { method: 'POST' }, 90000);
    return result.data ?? null;
  }
};
