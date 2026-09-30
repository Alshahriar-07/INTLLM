import { WebSource } from '../../types';
import { apiRequest } from '../api/client';

export interface WebServiceResponse {
  connected: boolean;
  sources: WebSource[];
  error?: string;
}

export const webService = {
  async searchWeb(query: string): Promise<WebServiceResponse> {
    const result = await apiRequest<{ connected: boolean; sources: WebSource[]; error?: string }>(
      `/web/search?q=${encodeURIComponent(query)}`
    );
    if (!result.ok || !result.data) {
      return { connected: false, sources: [], error: result.error };
    }
    return {
      connected: result.data.connected,
      sources: result.data.sources ?? [],
      error: result.data.error
    };
  }
};
