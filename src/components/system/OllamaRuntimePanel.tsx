import React, { useState } from 'react';
import {
  Play,
  Square,
  RefreshCw,
  Server,
  AlertTriangle,
  Loader2,
  CircleDot
} from 'lucide-react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { useIntllm } from '../../hooks/use-intllm';
import { OllamaRuntimeState } from '../../lib/services/ollamaService';

const STATE_META: Record<
  OllamaRuntimeState,
  { label: string; dot: string; badge: 'emerald' | 'amber' | 'rose' | 'cyan' | 'outline' }
> = {
  running: { label: 'Running', dot: 'bg-success', badge: 'emerald' },
  stopped: { label: 'Stopped', dot: 'bg-muted', badge: 'outline' },
  starting: { label: 'Starting…', dot: 'bg-accent animate-pulse', badge: 'cyan' },
  stopping: { label: 'Stopping…', dot: 'bg-warning animate-pulse', badge: 'amber' },
  unavailable: { label: 'Unavailable', dot: 'bg-warning', badge: 'amber' },
  error: { label: 'Error', dot: 'bg-error', badge: 'rose' }
};

const formatBytes = (bytes?: number | null): string => {
  if (bytes == null || !Number.isFinite(bytes)) return 'N/A';
  const gb = bytes / 1024 ** 3;
  if (gb >= 0.1) return `${gb.toFixed(2)} GB`;
  const mb = bytes / 1024 ** 2;
  return `${mb.toFixed(0)} MB`;
};

export const OllamaRuntimePanel: React.FC = () => {
  const {
    ollama,
    ollamaError,
    ollamaTransitioning,
    startOllama,
    stopOllama,
    restartOllama,
    refreshOllama
  } = useIntllm();
  const [busy, setBusy] = useState<'start' | 'stop' | 'restart' | 'refresh' | null>(null);

  const status = ollama?.status ?? 'unavailable';
  const meta = STATE_META[status];
  const running = status === 'running';

  const run = async (action: 'start' | 'stop' | 'restart' | 'refresh') => {
    setBusy(action);
    try {
      if (action === 'start') await startOllama();
      else if (action === 'stop') await stopOllama();
      else if (action === 'restart') await restartOllama();
      else await refreshOllama();
    } finally {
      setBusy(null);
    }
  };

  const lastChecked = ollama?.lastChecked ? new Date(ollama.lastChecked) : null;

  return (
    <Card className="p-4 space-y-4 border-border bg-surface">
      {/* Panel header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${meta.dot}`} />
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-bold font-mono text-primary">
                OLLAMA RUNTIME
              </h2>
              <Badge variant={meta.badge} size="sm">
                {meta.label}
              </Badge>
            </div>
            <span className="text-[11px] text-muted font-mono">
              {ollama?.endpoint ?? 'http://127.0.0.1:11434'}
            </span>
          </div>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <Button
            variant="primary"
            size="sm"
            onClick={() => run('start')}
            disabled={running || ollamaTransitioning || busy !== null}
            title="Start the local Ollama daemon"
          >
            {busy === 'start' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
            Start
          </Button>
          <Button
            variant="danger"
            size="sm"
            onClick={() => run('stop')}
            disabled={!running || ollamaTransitioning || busy !== null}
            title="Stop the local Ollama daemon"
          >
            {busy === 'stop' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Square className="w-3.5 h-3.5" />}
            Stop
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => run('restart')}
            disabled={ollamaTransitioning || busy !== null}
            title="Restart the local Ollama daemon"
          >
            {busy === 'restart' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
            Restart
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => run('refresh')}
            disabled={ollamaTransitioning || busy !== null}
            title="Refresh status"
            aria-label="Refresh Ollama status"
          >
            {busy === 'refresh' ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <RefreshCw className="w-3.5 h-3.5" />
            )}
          </Button>
        </div>
      </div>

      {/* Real error surfaced by the backend */}
      {(ollamaError || ollama?.reason) && !running && (
        <div className="flex items-start gap-2 p-2.5 rounded bg-error/5 border border-error/25 text-[11px] font-mono text-error">
          <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
          <span className="break-words">{ollamaError || ollama?.reason}</span>
        </div>
      )}

      {/* Details — only real values; N/A when the daemon does not report one */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs font-mono">
        <div className="p-2.5 bg-panel-hover border border-border rounded space-y-0.5">
          <div className="text-[10px] text-muted flex items-center gap-1">
            <CircleDot className="w-3 h-3" /> Version
          </div>
          <div className="text-primary truncate">
            {running ? ollama?.version ?? 'N/A' : 'N/A'}
          </div>
        </div>
        <div className="p-2.5 bg-panel-hover border border-border rounded space-y-0.5">
          <div className="text-[10px] text-muted flex items-center gap-1">
            <Server className="w-3 h-3" /> Models
          </div>
          <div className="text-primary">
            {running ? ollama?.modelCount ?? 'N/A' : 'N/A'}
          </div>
        </div>
        <div className="p-2.5 bg-panel-hover border border-border rounded space-y-0.5">
          <div className="text-[10px] text-muted">Loaded Models</div>
          <div className="text-primary truncate">
            {running
              ? ollama?.loadedModels?.length
                ? ollama.loadedModels.map((m) => m.name).join(', ')
                : 'None resident'
              : 'N/A'}
          </div>
        </div>
        <div className="p-2.5 bg-panel-hover border border-border rounded space-y-0.5">
          <div className="text-[10px] text-muted">Memory (VRAM)</div>
          <div className="text-primary">
            {running && ollama?.memory ? formatBytes(ollama.memory.vramUsedBytes) : 'N/A'}
          </div>
        </div>
      </div>

      <div className="text-[10px] text-muted font-mono">
        Last checked:{' '}
        {lastChecked && !Number.isNaN(lastChecked.getTime())
          ? lastChecked.toLocaleTimeString()
          : 'N/A'}
      </div>
    </Card>
  );
};
