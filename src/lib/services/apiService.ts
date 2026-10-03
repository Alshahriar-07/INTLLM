import { ApiKey } from '../../types';
import { apiRequest, OPENAI_BASE } from '../api/client';

export type ApiAccessMode = 'local' | 'lan';
export type ApiServerState = 'starting' | 'running' | 'stopped' | 'error' | 'restarting';

/** Real status of the local OpenAI-compatible API server. */
export interface ApiServerStatus {
  state: ApiServerState;
  reachable: boolean;
  accessMode: ApiAccessMode;
  storedAccessMode: ApiAccessMode;
  lanEnabled: boolean;
  requiresRestart: boolean;
  bindHost: string;
  port: number;
  localBaseUrl: string;
  lanBaseUrl: string | null;
  lanAddresses: string[];
  keyCount: number;
  hasKey: boolean;
  keyStoreAvailable: boolean;
  detail?: string | null;
  checkedAt: string;
  ollama?: { status: string; detail?: string | null } | null;
}

export interface ApiServiceResponse {
  /** True only when the API is actually reachable AND the key store is up. */
  connected: boolean;
  server: ApiServerStatus | null;
  keys: ApiKey[];
  keyStoreAvailable: boolean;
  baseUrl: string;
  error?: string;
}

export interface CreatedApiKey {
  key: ApiKey;
  /** Shown exactly once at creation/regeneration time. */
  secret: string;
}

interface ApiKeysDto {
  connected: boolean;
  keys: ApiKey[];
  baseUrl: string;
  error?: string;
}

export const apiService = {
  async getApiStatus(): Promise<ApiServiceResponse> {
    const [serverResult, keysResult] = await Promise.all([
      apiRequest<ApiServerStatus>('/api-server/status'),
      apiRequest<ApiKeysDto>('/api-keys')
    ]);

    const server = serverResult.ok ? serverResult.data ?? null : null;
    const keys = keysResult.ok ? keysResult.data?.keys ?? [] : [];
    const keyStoreAvailable = Boolean(keysResult.ok && keysResult.data?.connected);
    const connected = Boolean(server?.reachable && keyStoreAvailable);
    const baseUrl =
      server?.localBaseUrl ??
      keysResult.data?.baseUrl ??
      OPENAI_BASE ??
      'http://127.0.0.1:8000/v1';

    return {
      connected,
      server,
      keys,
      keyStoreAvailable,
      baseUrl,
      error: serverResult.error || keysResult.error
    };
  },

  async setAccessMode(mode: ApiAccessMode): Promise<ApiServerStatus | null> {
    const result = await apiRequest<ApiServerStatus>('/api-server/access', {
      method: 'POST',
      body: JSON.stringify({ mode })
    });
    return result.ok ? result.data ?? null : null;
  },

  async createKey(name: string, scopes: string[] = []): Promise<CreatedApiKey | null> {
    const result = await apiRequest<CreatedApiKey>('/api-keys', {
      method: 'POST',
      body: JSON.stringify({ name, scopes })
    });
    return result.ok ? result.data ?? null : null;
  },

  async regenerateKey(id: string): Promise<CreatedApiKey | null> {
    const result = await apiRequest<CreatedApiKey>(`/api-keys/${id}/regenerate`, {
      method: 'POST'
    });
    return result.ok ? result.data ?? null : null;
  },

  async revokeKey(id: string): Promise<boolean> {
    return (await apiRequest(`/api-keys/${id}`, { method: 'DELETE' })).ok;
  }
};
