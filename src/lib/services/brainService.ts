import { MemoryItem } from '../../types';
import { apiRequest } from '../api/client';

export interface BrainStats {
  totalMemories: number;
  hitRatePercent: number | null;
  avgLookupTimeMs: number | null;
  freshnessPercent: number | null;
  byLayer?: Record<string, number>;
}

export interface BrainServiceResponse {
  connected: boolean;
  memories: MemoryItem[];
  stats: BrainStats | null;
  error?: string;
}

interface BrainApiResponse {
  connected: boolean;
  memories: MemoryItem[];
  stats: BrainStats | null;
  error?: string;
}

export const brainService = {
  async getBrainMemories(params: {
    q?: string;
    layer?: 'L0' | 'L1' | 'L2';
    status?: string;
  } = {}): Promise<BrainServiceResponse> {
    const search = new URLSearchParams();
    if (params.q) search.set('q', params.q);
    if (params.layer) search.set('layer', params.layer);
    if (params.status) search.set('status', params.status);
    const query = search.toString();

    const result = await apiRequest<BrainApiResponse>(`/brain/memories${query ? `?${query}` : ''}`);
    if (!result.ok || !result.data) {
      return { connected: false, memories: [], stats: null, error: result.error };
    }
    return {
      connected: result.data.connected,
      memories: result.data.memories ?? [],
      stats: result.data.stats ?? null,
      error: result.data.error
    };
  },

  async searchMemories(query: string): Promise<BrainServiceResponse> {
    const result = await apiRequest<BrainApiResponse>(
      `/brain/search?q=${encodeURIComponent(query)}`
    );
    if (!result.ok || !result.data) {
      return { connected: false, memories: [], stats: null, error: result.error };
    }
    return {
      connected: result.data.connected,
      memories: result.data.memories ?? [],
      stats: null,
      error: result.data.error
    };
  }
};
