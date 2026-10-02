import { AgentOperation, AgentWorkspace } from '../../types';
import { apiRequest } from '../api/client';

/** Agent mode API service. All filesystem/terminal work runs on the backend. */
export const agentService = {
  async getStatus(): Promise<AgentWorkspace | null> {
    const result = await apiRequest<AgentWorkspace>('/agent/status');
    return result.ok ? (result.data ?? null) : null;
  },

  async setWorkspace(path: string): Promise<AgentWorkspace | null> {
    const result = await apiRequest<AgentWorkspace>('/agent/workspace', {
      method: 'POST',
      body: JSON.stringify({ path })
    });
    return result.ok ? (result.data ?? null) : null;
  },

  /** Ask the backend to open the local OS folder chooser (best-effort). */
  async pickWorkspace(): Promise<AgentWorkspace | null> {
    const result = await apiRequest<AgentWorkspace>('/agent/workspace/pick', {
      method: 'POST'
    });
    return result.ok ? (result.data ?? null) : null;
  },

  async clearWorkspace(): Promise<AgentWorkspace | null> {
    const result = await apiRequest<AgentWorkspace>('/agent/workspace', { method: 'DELETE' });
    return result.ok ? (result.data ?? null) : null;
  },

  async list(path?: string): Promise<AgentOperation | null> {
    const q = path ? `?path=${encodeURIComponent(path)}` : '';
    const result = await apiRequest<AgentOperation>(`/agent/fs/list${q}`);
    return result.ok ? (result.data ?? null) : null;
  },

  async read(path: string): Promise<AgentOperation | null> {
    const result = await apiRequest<AgentOperation>(
      `/agent/fs/read?path=${encodeURIComponent(path)}`
    );
    return result.ok ? (result.data ?? null) : null;
  },

  async search(query: string, path?: string): Promise<AgentOperation | null> {
    const q = new URLSearchParams({ query });
    if (path) q.set('path', path);
    const result = await apiRequest<AgentOperation>(`/agent/fs/search?${q.toString()}`);
    return result.ok ? (result.data ?? null) : null;
  },

  async write(
    path: string,
    content: string,
    decision?: 'allow' | 'allow_session' | 'deny'
  ): Promise<AgentOperation | null> {
    const result = await apiRequest<AgentOperation>('/agent/fs/write', {
      method: 'POST',
      body: JSON.stringify({ path, content, decision })
    });
    return result.ok ? (result.data ?? null) : null;
  },

  async mkdir(
    path: string,
    decision?: 'allow' | 'allow_session' | 'deny'
  ): Promise<AgentOperation | null> {
    const result = await apiRequest<AgentOperation>('/agent/fs/mkdir', {
      method: 'POST',
      body: JSON.stringify({ path, decision })
    });
    return result.ok ? (result.data ?? null) : null;
  },

  async remove(
    path: string,
    decision?: 'allow' | 'allow_session' | 'deny'
  ): Promise<AgentOperation | null> {
    const result = await apiRequest<AgentOperation>('/agent/fs/delete', {
      method: 'POST',
      body: JSON.stringify({ path, decision })
    });
    return result.ok ? (result.data ?? null) : null;
  },

  async move(
    source: string,
    destination: string,
    decision?: 'allow' | 'allow_session' | 'deny'
  ): Promise<AgentOperation | null> {
    const result = await apiRequest<AgentOperation>('/agent/fs/move', {
      method: 'POST',
      body: JSON.stringify({ source, destination, decision })
    });
    return result.ok ? (result.data ?? null) : null;
  },

  async terminal(
    command: string,
    cwd?: string,
    decision?: 'allow' | 'allow_session' | 'deny'
  ): Promise<AgentOperation | null> {
    const result = await apiRequest<AgentOperation>('/agent/terminal', {
      method: 'POST',
      body: JSON.stringify({ command, cwd, decision })
    });
    return result.ok ? (result.data ?? null) : null;
  },

  async grantSession(operation: string): Promise<string[]> {
    const result = await apiRequest<{ session_grants: string[] }>('/agent/permissions', {
      method: 'POST',
      body: JSON.stringify({ operation, decision: 'allow_session' })
    });
    return result.data?.session_grants ?? [];
  }
};
