import React from 'react';
import { AlertTriangle, RefreshCw, Database, Brain, WifiOff } from 'lucide-react';
import { Button } from './Button';

interface ServiceInfo {
  status?: string;
  detail?: string | null;
}

interface DegradedModeBannerProps {
  services: Record<string, ServiceInfo | undefined>;
  onRefresh: () => void;
}

export const DegradedModeBanner: React.FC<DegradedModeBannerProps> = ({ services, onRefresh }) => {
  const postgresStatus = services?.postgres?.status;
  const memoryStatus = services?.memory?.status;
  const ollamaStatus = services?.ollama?.status;
  
  const hasPostgresIssue = postgresStatus && postgresStatus !== 'connected';
  const hasMemoryIssue = memoryStatus && memoryStatus !== 'connected';
  const hasOllamaIssue = ollamaStatus && ollamaStatus !== 'connected';
  
  if (!hasPostgresIssue && !hasMemoryIssue && !hasOllamaIssue) {
    return null;
  }

  return (
    <div className="flex items-start gap-3 px-4 py-3 bg-warning/10 border-b border-warning/20 text-warning text-xs font-mono">
      <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        <div className="font-semibold mb-1">Degraded Mode — Some services are unavailable</div>
        <div className="space-y-1 text-secondary">
          {hasPostgresIssue && (
            <div className="flex items-center gap-2">
              <Database className="w-3 h-3 shrink-0" />
              <span>PostgreSQL: {postgresStatus} {services.postgres?.detail ? `— ${services.postgres.detail}` : ''}</span>
            </div>
          )}
          {hasMemoryIssue && (
            <div className="flex items-center gap-2">
              <Brain className="w-3 h-3 shrink-0" />
              <span>Memory: {memoryStatus} {services.memory?.detail ? `— ${services.memory.detail}` : ''}</span>
            </div>
          )}
          {hasOllamaIssue && (
            <div className="flex items-center gap-2">
              <WifiOff className="w-3 h-3 shrink-0" />
              <span>Ollama: {ollamaStatus} {services.ollama?.detail ? `— ${services.ollama.detail}` : ''}</span>
            </div>
          )}
        </div>
        <p className="mt-2 text-secondary">
          Chat history, memory features, and API key management require PostgreSQL.
          Continue with limited functionality or retry.
        </p>
      </div>
      <Button
        variant="outline"
        size="sm"
        onClick={onRefresh}
        className="shrink-0"
      >
        <RefreshCw className="w-3.5 h-3.5 mr-1" />
        Retry
      </Button>
    </div>
  );
};
