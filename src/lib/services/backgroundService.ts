import { BackgroundTask } from '../../types';
import { apiRequest } from '../api/client';

export interface BackgroundServiceResponse {
  connected: boolean;
  tasks: BackgroundTask[];
  isThrottled: boolean;
  paused: boolean;
  state: string;
  error?: string;
}

export const backgroundService = {
  async getTaskQueue(): Promise<BackgroundServiceResponse> {
    const result = await apiRequest<{
      connected: boolean;
      tasks: BackgroundTask[];
      isThrottled: boolean;
      paused: boolean;
      state: string;
      error?: string;
    }>('/background/status');
    if (!result.ok || !result.data) {
      return {
        connected: false,
        tasks: [],
        isThrottled: false,
        paused: false,
        state: 'NORMAL',
        error: result.error
      };
    }
    return {
      connected: result.data.connected,
      tasks: result.data.tasks ?? [],
      isThrottled: result.data.isThrottled,
      paused: result.data.paused,
      state: result.data.state,
      error: result.data.error
    };
  },

  async pause(): Promise<boolean> {
    return (await apiRequest('/background/pause', { method: 'POST' })).ok;
  },

  async resume(): Promise<boolean> {
    return (await apiRequest('/background/resume', { method: 'POST' })).ok;
  }
};
