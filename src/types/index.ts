export type NavigationTab = 
  | 'overview'
  | 'chat'
  | 'models'
  | 'brain'
  | 'web'
  | 'browser'
  | 'tools'
  | 'api'
  | 'system'
  | 'docs'
  | 'settings';

export type ActivityStepType = 
  | 'thinking'
  | 'flash_brain'
  | 'hot_cache'
  | 'secondary_brain'
  | 'web_search'
  | 'tool'
  | 'verification';

export interface ActivityStep {
  id: string;
  type: ActivityStepType;
  label: string;
  status: 'running' | 'completed' | 'failed' | 'stale' | 'skipped';
  latencyMs?: number;
  detail?: string;
  metadata?: Record<string, unknown>;
}

export interface WebSource {
  id: string;
  domain: string;
  title: string;
  url: string;
  timestamp: string;
  trustScore: number; // 0 to 100
  verified: boolean;
  snippet: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  model?: string;
  activities?: ActivityStep[];
  sources?: WebSource[];
  memoryUsed?: number; // count of memories used
  tokensPerSec?: number;
  isStreaming?: boolean;
}

export type HardwareTier = 'POTATO' | 'NEUTRAL' | 'I PAID FOR MY WHOLE PC';

export interface Model {
  id: string;
  name: string;
  parameterSize: string;
  quantization: string;
  contextWindow: string;
  memoryReqGB: number;
  tier: HardwareTier;
  capabilities: string[];
  installed: boolean;
  isDefault: boolean;
  downloadProgress?: number; // undefined or 0-100
  family: string;
}

export interface MemoryItem {
  id: string;
  title: string;
  layer: 'L0' | 'L1' | 'L2';
  type: 'fact' | 'workflow' | 'lesson' | 'preference';
  confidence: number; // 0-100
  freshnessScore: number; // 0-100
  source: string;
  lastVerified: string;
  status: 'active' | 'stale' | 'archived';
  keywords: string[];
  rawSnippet: string;
  vectorId: string;
}

export interface BrowserTab {
  id: string;
  title: string;
  url: string;
  active: boolean;
  favicon?: string;
}

export interface BrowserActivity {
  id: string;
  timestamp: string;
  action: string;
  detail: string;
  status: 'pending_approval' | 'allowed' | 'denied' | 'completed';
  targetElement?: string;
  url?: string;
}

export type SecurityLevel = 'read-only' | 'requires-approval' | 'restricted';

export interface Tool {
  id: string;
  name: string;
  category: 'web' | 'browser' | 'filesystem' | 'terminal' | 'system';
  description: string;
  permissionLevel: SecurityLevel;
  enabled: boolean;
  riskScore: 'Low' | 'Medium' | 'High' | 'Critical';
}

export interface ApiKey {
  id: string;
  name: string;
  key: string;
  created: string;
  lastUsed: string;
  scopes: string[];
  status: 'active' | 'revoked';
}

export interface SystemStatus {
  cpu: {
    name: string;
    usage: number; // percentage
    cores: number;
  };
  ram: {
    usedGB: number;
    totalGB: number;
  };
  gpu: {
    name: string;
    vramUsedGB: number;
    vramTotalGB: number;
    usage: number;
  };
  disk: {
    freeGB: number;
    totalGB: number;
  };
  services: {
    intllm: boolean;
    ollama: boolean;
    postgres: boolean;
    web: boolean;
    browser: boolean;
  };
}

export interface BackgroundTask {
  id: string;
  name: string;
  priority: 'P0 (Interactive)' | 'P1 (Tool)' | 'P2 (Maintenance)' | 'P3 (Cleanup)';
  status: 'queued' | 'running' | 'throttled' | 'paused' | 'completed' | 'failed';
  progress: number;
  currentAction: string;
  cpuBudget: 'Low' | 'Medium' | 'High';
}
