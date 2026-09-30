import { Tool } from '../../types';
import { apiRequest } from '../api/client';

/** Static capability schemas mirror the backend registry (UI fallback only). */
export const staticToolSchemas: Tool[] = [
  {
    id: 'web.search',
    name: 'Web Search Gateway',
    category: 'web',
    description: 'Queries live search engines for real-time documentation and news.',
    permissionLevel: 'read-only',
    enabled: true,
    riskScore: 'Low'
  },
  {
    id: 'web.extract',
    name: 'Web Page Extractor',
    category: 'web',
    description: 'Extracts clean HTML/Markdown text from target URL web pages.',
    permissionLevel: 'read-only',
    enabled: true,
    riskScore: 'Low'
  },
  {
    id: 'browser.read',
    name: 'Headless Browser Reader',
    category: 'browser',
    description: 'Navigates and inspects JavaScript-rendered DOM elements via Playwright.',
    permissionLevel: 'read-only',
    enabled: true,
    riskScore: 'Low'
  },
  {
    id: 'browser.click',
    name: 'Browser Action Clicker',
    category: 'browser',
    description: 'Triggers mouse clicks, input selections, and form submissions.',
    permissionLevel: 'requires-approval',
    enabled: true,
    riskScore: 'Medium'
  },
  {
    id: 'filesystem.read',
    name: 'Local Directory Reader',
    category: 'filesystem',
    description: 'Reads local workspace files, project structures, and code files.',
    permissionLevel: 'requires-approval',
    enabled: true,
    riskScore: 'Medium'
  },
  {
    id: 'filesystem.write',
    name: 'Local File Writer',
    category: 'filesystem',
    description: 'Creates, edits, or deletes files inside approved workspace paths.',
    permissionLevel: 'restricted',
    enabled: false,
    riskScore: 'High'
  },
  {
    id: 'terminal.execute',
    name: 'Terminal Subprocess Executor',
    category: 'terminal',
    description: 'Executes shell commands in isolated subshells.',
    permissionLevel: 'restricted',
    enabled: false,
    riskScore: 'Critical'
  },
  {
    id: 'system.info',
    name: 'Hardware & Process Monitor',
    category: 'system',
    description: 'Reads CPU, VRAM, and RAM metrics from local system runtime.',
    permissionLevel: 'read-only',
    enabled: true,
    riskScore: 'Low'
  }
];

export interface ToolServiceResponse {
  connected: boolean;
  tools: Tool[];
  error?: string;
}

export interface ToolRunResult {
  tool: string;
  status: string;
  output?: Record<string, unknown> | null;
  error?: string | null;
  permission?: string | null;
}

export const toolService = {
  async getTools(): Promise<ToolServiceResponse> {
    const result = await apiRequest<{ connected: boolean; tools: Tool[]; error?: string }>(
      '/tools'
    );
    if (!result.ok || !result.data) {
      return { connected: false, tools: staticToolSchemas, error: result.error };
    }
    return {
      connected: result.data.connected,
      tools: result.data.tools ?? staticToolSchemas,
      error: result.data.error
    };
  },

  async runTool(
    toolId: string,
    args: Record<string, unknown>,
    decision?: 'allow' | 'allow_session' | 'deny'
  ): Promise<ToolRunResult | null> {
    const result = await apiRequest<ToolRunResult>(`/tools/${toolId}/run`, {
      method: 'POST',
      body: JSON.stringify({ arguments: args, decision })
    });
    return result.data ?? null;
  }
};
