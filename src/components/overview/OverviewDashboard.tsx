import React, { useEffect, useState } from 'react';
import { Activity, ArrowRight, Brain, Compass, Cpu, Globe, Layers, ShieldCheck, Terminal } from 'lucide-react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { StatusDot } from '../ui/StatusDot';
import { NavigationTab } from '../../types';
import { useIntllm } from '../../hooks/use-intllm';
import { brainService, BrainStats } from '../../lib/services/brainService';
import { backgroundService } from '../../lib/services/backgroundService';
import { cn } from '../../lib/utils';

export interface OverviewDashboardProps {
  onNavigate: (tab: NavigationTab) => void;
}

export const OverviewDashboard: React.FC<OverviewDashboardProps> = ({ onNavigate }) => {
  const intllm = useIntllm();
  const connected = intllm.connected;
  const modelCount = intllm.models.filter((m) => m.installed).length;
  const [brainStats, setBrainStats] = useState<BrainStats | null>(null);
  const [bgState, setBgState] = useState<{ state: string; tasks: number } | null>(null);

  useEffect(() => {
    let active = true;
    if (!connected) {
      setBrainStats(null);
      setBgState(null);
      return;
    }
    brainService.getBrainMemories().then((result) => {
      if (active) setBrainStats(result.stats);
    });
    backgroundService.getTaskQueue().then((result) => {
      if (active) setBgState({ state: result.state, tasks: result.tasks.length });
    });
    return () => {
      active = false;
    };
  }, [connected]);

  const serviceState = (key: string, up: boolean) => (connected && up ? 'ready' : connected ? 'idle' : 'offline');

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-6xl mx-auto px-4 md:px-6 py-6 space-y-5">
        {/* Title */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-4">
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-xl font-semibold tracking-tight text-primary">Overview</h1>
              <Badge variant={connected ? 'emerald' : 'outline'} dot>
                {connected ? 'Connected' : 'Offline'}
              </Badge>
            </div>
            <p className="text-xs text-secondary mt-1">
              Local-first AI infrastructure — layered memory, live retrieval, browser tools, and an
              OpenAI-compatible local API.
            </p>
          </div>
          <Button variant="primary" size="md" onClick={() => onNavigate('chat')} className="shrink-0">
            Open Chat <ArrowRight className="w-3.5 h-3.5" aria-hidden />
          </Button>
        </div>

        {/* System status strip */}
        <Card className="p-4 space-y-2.5">
          <div className="flex items-center justify-between border-b border-border pb-2 mb-1">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-muted flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5" aria-hidden /> System status
            </h2>
            <button
              onClick={() => onNavigate('system')}
              className="text-[11px] font-mono text-muted hover:text-primary transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring rounded"
            >
              Details →
            </button>
          </div>
          <StatusDot label="Ollama" state={serviceState('ollama', intllm.services?.ollama?.status === 'connected')} />
          <StatusDot label="Brain" state={connected ? 'active' : 'offline'} />
          <StatusDot label="Internet" state={serviceState('web', intllm.services?.web?.status === 'connected')} />
          <StatusDot label="Browser" state={serviceState('browser', intllm.services?.browser?.status === 'connected')} />
          <StatusDot
            label="Learning"
            state={connected ? (bgState && bgState.tasks > 0 ? 'active' : 'idle') : 'offline'}
            meta={bgState ? `${bgState.tasks} task${bgState.tasks === 1 ? '' : 's'}` : undefined}
          />
        </Card>

        {/* Metric cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="space-y-1.5">
            <div className="flex items-center justify-between text-xs text-muted font-mono">
              <span>Active model</span>
              <Cpu className="w-4 h-4" aria-hidden />
            </div>
            <div className="text-sm font-semibold font-mono text-primary truncate">
              {connected && intllm.currentModelId ? intllm.currentModelId : 'None'}
            </div>
            <div className="text-[11px] text-muted font-mono">
              {modelCount > 0 ? `${modelCount} installed` : 'Connect Ollama'}
            </div>
          </Card>

          <Card className="space-y-1.5">
            <div className="flex items-center justify-between text-xs text-muted font-mono">
              <span>Flash brain hit rate</span>
              <Brain className="w-4 h-4" aria-hidden />
            </div>
            <div className="text-2xl font-semibold font-mono text-primary">
              {brainStats?.hitRatePercent != null ? `${Math.round(brainStats.hitRatePercent)}%` : '—'}
            </div>
            <div className="text-[11px] text-muted font-mono">
              {brainStats
                ? `${brainStats.totalMemories} indexed memories`
                : connected
                  ? 'Memory stats unavailable'
                  : 'Runtime offline'}
            </div>
          </Card>

          <Card className="space-y-1.5">
            <div className="flex items-center justify-between text-xs text-muted font-mono">
              <span>Live web</span>
              <Globe className="w-4 h-4" aria-hidden />
            </div>
            <div className="text-sm font-semibold font-mono text-primary">
              {connected && intllm.services?.web?.status === 'connected' ? 'Online' : 'Unavailable'}
            </div>
            <div className="text-[11px] text-muted font-mono">Retrieval gateway</div>
          </Card>

          <Card className="space-y-1.5">
            <div className="flex items-center justify-between text-xs text-muted font-mono">
              <span>Background learning</span>
              <Activity className="w-4 h-4" aria-hidden />
            </div>
            <div className="text-sm font-semibold font-mono text-primary">{bgState ? bgState.state : '—'}</div>
            <div className="text-[11px] text-muted font-mono">
              {bgState ? `${bgState.tasks} queued task(s)` : 'Maintenance engine unavailable'}
            </div>
          </Card>
        </div>

        {/* Memory pipeline */}
        <Card className="p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-border pb-2.5">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-accent" aria-hidden />
              <h2 className="text-sm font-medium text-primary">Reasoning &amp; memory pipeline</h2>
            </div>
            <span className="hidden md:block text-[11px] font-mono text-muted">Query → L0 → L1/L2 → Live web</span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-5 gap-2 text-xs font-mono">
            {[
              { step: '1', label: 'User request', meta: 'Priority P0', color: 'text-primary' },
              { step: 'L0', label: 'Flash brain', meta: 'Routing index', color: 'text-accent' },
              { step: 'L1/L2', label: 'Hot cache & PG', meta: 'Vector storage', color: 'text-accent' },
              { step: 'LW', label: 'Live web & browser', meta: 'Retrieval gateway', color: 'text-success' },
              { step: 'LLM', label: 'Ollama inference', meta: 'Local runtime', color: 'text-warning' }
            ].map((node) => (
              <div
                key={node.step}
                className="p-3 bg-canvas border border-border rounded-md space-y-0.5 text-center"
              >
                <div className={cn('text-[10px] font-semibold', node.color)}>{node.step}</div>
                <div className="text-xs font-medium text-primary">{node.label}</div>
                <div className="text-[10px] text-muted">{node.meta}</div>
              </div>
            ))}
          </div>
        </Card>

        {/* Bottom: activity + navigation */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2">
            <Card className="p-6 text-center space-y-1.5">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-muted">Recent activity</h2>
              <p className="text-xs text-secondary">No recent activity recorded</p>
              <p className="text-[11px] text-muted">
                Runtime telemetry appears here once the backend is connected and inference begins.
              </p>
            </Card>
          </div>

          <div className="space-y-2">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-muted flex items-center gap-1.5">
              <Terminal className="w-3.5 h-3.5" aria-hidden /> Workspace
            </h2>
            <Button variant="outline" className="w-full justify-between h-9 text-xs" onClick={() => onNavigate('models')}>
              <span className="flex items-center gap-2">
                <Cpu className="w-4 h-4 text-accent" aria-hidden /> Model manager
              </span>
              <ArrowRight className="w-3.5 h-3.5" aria-hidden />
            </Button>
            <Button variant="outline" className="w-full justify-between h-9 text-xs" onClick={() => onNavigate('brain')}>
              <span className="flex items-center gap-2">
                <Brain className="w-4 h-4 text-accent" aria-hidden /> Brain &amp; memory
              </span>
              <ArrowRight className="w-3.5 h-3.5" aria-hidden />
            </Button>
            <Button variant="outline" className="w-full justify-between h-9 text-xs" onClick={() => onNavigate('browser')}>
              <span className="flex items-center gap-2">
                <Compass className="w-4 h-4 text-success" aria-hidden /> Browser agent
              </span>
              <ArrowRight className="w-3.5 h-3.5" aria-hidden />
            </Button>
            <div className="flex items-center gap-1.5 px-1 pt-1 text-[11px] text-muted">
              <ShieldCheck className="w-3 h-3 text-success" aria-hidden />
              All data remains on this device
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
