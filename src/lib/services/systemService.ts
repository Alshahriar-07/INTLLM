import { SystemStatus } from '../../types';
import { apiRequest } from '../api/client';

export interface SystemServiceResponse {
  connected: boolean;
  status: SystemStatus | null;
  processes: any[];
  error?: string;
}

export const systemService = {
  async getSystemTelemetry(): Promise<SystemServiceResponse> {
    const result = await apiRequest<SystemStatus>('/system');
    if (!result.ok || !result.data) {
      return { connected: false, status: null, processes: [], error: result.error };
    }
    return { connected: true, status: result.data, processes: [] };
  }
};
