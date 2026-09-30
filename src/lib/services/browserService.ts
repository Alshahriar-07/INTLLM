import { BrowserTab, BrowserActivity } from '../../types';
import { apiRequest } from '../api/client';

export interface BrowserServiceResponse {
  connected: boolean;
  active: boolean;
  tabs: BrowserTab[];
  activities: BrowserActivity[];
  screenshot?: string | null;
  error?: string;
}

interface BrowserStateDto {
  connected: boolean;
  active: boolean;
  tabs: BrowserTab[];
  screenshot?: string | null;
  error?: string;
}

export const browserService = {
  async getBrowserState(): Promise<BrowserServiceResponse> {
    const result = await apiRequest<BrowserStateDto>('/browser/status');
    if (!result.ok || !result.data) {
      return {
        connected: false,
        active: false,
        tabs: [],
        activities: [],
        error: result.error
      };
    }
    return {
      connected: result.data.connected,
      active: result.data.active,
      tabs: result.data.tabs ?? [],
      activities: [],
      screenshot: result.data.screenshot,
      error: result.data.error
    };
  },

  async action(
    action: 'open' | 'read' | 'click' | 'screenshot',
    options: { url?: string; selector?: string; decision?: 'allow' | 'allow_session' | 'deny' } = {}
  ): Promise<any> {
    const result = await apiRequest('/browser/action', {
      method: 'POST',
      body: JSON.stringify({ action, ...options })
    });
    return result.data ?? null;
  }
};
