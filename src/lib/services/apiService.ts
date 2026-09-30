import { ApiKey } from '../../types';
import { apiRequest, OPENAI_BASE } from '../api/client';

export interface ApiServiceResponse {
  connected: boolean;
  keys: ApiKey[];
  baseUrl: string;
  error?: string;
}

export interface CreatedApiKey {
  key: ApiKey;
  /** Shown exactly once at creation time. */
  secret: string;
}

export const apiService = {
  async getApiStatus(): Promise<ApiServiceResponse> {
    const result = await apiRequest<{
      connected: boolean;
      keys: ApiKey[];
      baseUrl: string;
      error?: string;
    }>('/api-keys');
    if (!result.ok || !result.data) {
      return {
        connected: false,
        keys: [],
        baseUrl: OPENAI_BASE ?? 'http://127.0.0.1:8000/v1',
        error: result.error
      };
    }
    return {
      connected: result.data.connected,
      keys: result.data.keys ?? [],
      baseUrl: result.data.baseUrl,
      error: result.data.error
    };
  },

  async createKey(name: string, scopes: string[] = []): Promise<CreatedApiKey | null> {
    const result = await apiRequest<CreatedApiKey>('/api-keys', {
      method: 'POST',
      body: JSON.stringify({ name, scopes })
    });
    return result.data ?? null;
  },

  async revokeKey(id: string): Promise<boolean> {
    return (await apiRequest(`/api-keys/${id}`, { method: 'DELETE' })).ok;
  }
};
