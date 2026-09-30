import { Model } from '../../types';
import { apiRequest, openEventStream } from '../api/client';

export interface ModelServiceResponse {
  connected: boolean;
  models: Model[];
  error?: string;
}

export interface ModelRecommendation {
  name: string;
  tier?: string | null;
  memory_req_gb?: number | null;
  fits: boolean;
  utilization_percent?: number | null;
  installed: boolean;
}

export const modelService = {
  async getInstalledModels(): Promise<ModelServiceResponse> {
    const result = await apiRequest<{ connected: boolean; models: Model[]; error?: string }>(
      '/models'
    );
    if (!result.ok || !result.data) {
      return { connected: false, models: [], error: result.error };
    }
    return {
      connected: result.data.connected,
      models: result.data.models ?? [],
      error: result.data.error
    };
  },

  async getRecommendations(): Promise<ModelRecommendation[]> {
    const result = await apiRequest<{ recommendations: ModelRecommendation[] }>(
      '/models/recommend'
    );
    return result.data?.recommendations ?? [];
  },

  /** Streams real `ollama pull` progress from the backend. */
  pull(name: string, onProgress: (data: any) => void, onError?: (msg: string) => void): () => void {
    return openEventStream('/models/pull', { name }, {
      onEvent: (type, data) => {
        if (type === 'model.pull.failed') onError?.(data?.error ?? 'Model pull failed');
        else onProgress(data);
      },
      onError
    });
  },

  async deleteModel(name: string): Promise<boolean> {
    const result = await apiRequest(`/models/${encodeURIComponent(name)}`, { method: 'DELETE' });
    return result.ok;
  },

  async setDefault(name: string): Promise<boolean> {
    const result = await apiRequest('/models/default', {
      method: 'POST',
      body: JSON.stringify({ name })
    });
    return result.ok;
  }
};
