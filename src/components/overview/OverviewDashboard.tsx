import React, { useEffect, useState } from 'react';
import { 
  Brain, 
  Globe, 
  Cpu, 
  Activity, 
  ArrowRight, 
  Terminal, 
  Layers,
  WifiOff
} from 'lucide-react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { NavigationTab } from '../../types';
import { useIntllm } from '../../hooks/use-intllm';
import { brainService, BrainStats } from '../../lib/services/brainService';
import { backgroundService } from '../../lib/services/backgroundService';

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

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto overflow-y-auto max-h-[calc(100vh-3.5rem)]">
      {/* Title & Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-[#21262D] pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl font-bold font-mono tracking-tight text-slate-900 dark:text-slate-100">
              INTLLM OPERATING ENVIRONMENT
            </h1>
            <Badge variant={connected ? 'emerald' : 'outline'}>
              {connected ? 'CONNECTED' : 'DISCONNECTED'}
            </Badge>
          </div>
          <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
            Local-first AI infrastructure wrapping LLMs with live knowledge retrieval, layered memory, browser tools & OpenAI-compatible local API.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="primary" size="sm" onClick={() => onNavigate('chat')}>
            Open Chat Workspace <ArrowRight className="w-3.5 h-3.5 ml-1" />
          </Button>
        </div>
      </div>

      {/* Connection Notice Banner */}
      <Card
        className={`p-4 flex items-center justify-between text-xs font-mono border ${
          connected
            ? 'bg-emerald-50 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-800/40'
            : 'bg-amber-50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-800/40'
        }`}
      >
        <div
          className={`flex items-center gap-2.5 ${
            connected ? 'text-emerald-700 dark:text-emerald-400' : 'text-amber-800 dark:text-amber-400'
          }`}
        >
          {connected ? <Activity className="w-4 h-4 shrink-0" /> : <WifiOff className="w-4 h-4 shrink-0" />}
          <span>
            {connected
              ? `Local INTLLM runtime connected${intllm.version ? ` (v${intllm.version})` : ''}. Live inference and telemetry enabled.`
              : 'Local INTLLM runtime service is not connected. Connect the backend service to enable live inference & telemetry.'}
          </span>
        </div>
        <Badge variant={connected ? 'emerald' : 'amber'} size="sm">
          {connected ? 'Online' : 'Standby Mode'}
        </Badge>
      </Card>

      {/* Glance Disconnected Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 font-mono">
            <span>Active LLM Model</span>
            <Cpu className="w-4 h-4 text-slate-500" />
          </div>
          <div className="text-base font-semibold font-mono text-slate-700 dark:text-slate-300 truncate">
            {connected && intllm.currentModelId ? intllm.currentModelId : 'No Model Loaded'}
          </div>
          <div className="text-[11px] text-slate-500 font-mono">
            {modelCount > 0 ? `${modelCount} installed models` : 'Connect Ollama service'}
          </div>
        </Card>

        <Card className="space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 font-mono">
            <span>Flash Brain Hit Rate</span>
            <Brain className="w-4 h-4 text-slate-500" />
          </div>
          <div className="text-2xl font-bold font-mono text-slate-600 dark:text-slate-400">
            {brainStats?.hitRatePercent != null ? `${brainStats.hitRatePercent}%` : 'N/A'}
          </div>
          <div className="text-[11px] text-slate-500 font-mono">
            {brainStats
              ? `${brainStats.totalMemories} indexed memories`
              : connected
                ? 'Memory stats unavailable'
                : 'Connect INTLLM runtime'}
          </div>
        </Card>

        <Card className="space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 font-mono">
            <span>Live Web Retrieval</span>
            <Globe className="w-4 h-4 text-slate-500" />
          </div>
          <div className="text-2xl font-bold font-mono text-slate-600 dark:text-slate-400">
            {connected
              ? intllm.services?.web?.status === 'connected'
                ? 'Online'
                : 'N/A'
              : 'Offline'}
          </div>
          <div className="text-[11px] text-slate-500 font-mono">
            {connected
              ? intllm.services?.web?.status === 'connected'
                ? 'Web gateway connected'
                : 'Web gateway unavailable'
              : 'Web gateway standby'}
          </div>
        </Card>

        <Card className="space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 font-mono">
            <span>Background Maintenance</span>
            <Activity className="w-4 h-4 text-slate-500" />
          </div>
          <div className="text-base font-semibold font-mono text-slate-600 dark:text-slate-400">
            {bgState ? bgState.state : 'N/A'}
          </div>
          <div className="text-[11px] text-slate-500 font-mono">
            {bgState
              ? `${bgState.tasks} background task${bgState.tasks === 1 ? '' : 's'}`
              : 'Background engine unavailable'}
          </div>
        </Card>
      </div>

      {/* INTLLM System Topology Conceptual Diagram */}
      <Card className="p-5 space-y-4 border-slate-200 dark:border-[#21262D]">
        <div className="flex items-center justify-between border-b border-slate-200 dark:border-[#21262D] pb-3">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-cyan-500" />
            <h2 className="text-sm font-semibold font-mono text-slate-900 dark:text-slate-100">
              INTLLM REASONING & MEMORY PIPELINE ARCHITECTURE
            </h2>
          </div>
          <span className="text-xs text-slate-500 font-mono">Routing: Query → L0 → L1/L2 → Live Web</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-3 text-xs font-mono">
          <div className="p-3 bg-slate-50 dark:bg-[#161B22] border border-slate-200 dark:border-slate-800 rounded space-y-1 text-center">
            <div className="text-[10px] text-cyan-500 font-semibold">STEP 1</div>
            <div className="text-xs font-bold text-slate-700 dark:text-slate-300">User Request</div>
            <div className="text-[10px] text-slate-500">Priority P0</div>
          </div>

          <div className="p-3 bg-slate-50 dark:bg-[#161B22] border border-slate-200 dark:border-slate-800 rounded space-y-1 text-center">
            <div className="text-[10px] text-purple-400 font-semibold">L0 FLASH BRAIN</div>
            <div className="text-xs font-bold text-slate-700 dark:text-slate-300">Micro Index</div>
            <div className="text-[10px] text-slate-500">Routing Index</div>
          </div>

          <div className="p-3 bg-slate-50 dark:bg-[#161B22] border border-slate-200 dark:border-slate-800 rounded space-y-1 text-center">
            <div className="text-[10px] text-cyan-400 font-semibold">L1/L2 MEMORY</div>
            <div className="text-xs font-bold text-slate-700 dark:text-slate-300">Hot Cache & PG</div>
            <div className="text-[10px] text-slate-500">Vector Storage</div>
          </div>

          <div className="p-3 bg-slate-50 dark:bg-[#161B22] border border-slate-200 dark:border-slate-800 rounded space-y-1 text-center">
            <div className="text-[10px] text-emerald-400 font-semibold">LIVE WEB</div>
            <div className="text-xs font-bold text-slate-700 dark:text-slate-300">Web & Browser</div>
            <div className="text-[10px] text-slate-500">Retrieval Gateway</div>
          </div>

          <div className="p-3 bg-slate-50 dark:bg-[#161B22] border border-slate-200 dark:border-slate-800 rounded space-y-1 text-center">
            <div className="text-[10px] text-amber-400 font-semibold">OLLAMA LLM</div>
            <div className="text-xs font-bold text-slate-700 dark:text-slate-300">Base Inference</div>
            <div className="text-[10px] text-slate-500">Local Runtime</div>
          </div>
        </div>
      </Card>

      {/* Bottom Section: Recent Activity & Quick Navigation */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-3">
          <h2 className="text-sm font-semibold font-mono text-slate-800 dark:text-slate-200 flex items-center gap-2">
            <Activity className="w-4 h-4 text-cyan-500" />
            RECENT RUNTIME ACTIVITY
          </h2>
          <Card className="p-6 text-center space-y-2 border-slate-200 dark:border-[#21262D]">
            <div className="text-xs font-mono font-semibold text-slate-600 dark:text-slate-400">
              No recent activity recorded
            </div>
            <p className="text-xs text-slate-500 font-sans">
              Connect the INTLLM runtime to start logging inference queries, memory updates & tool executions.
            </p>
          </Card>
        </div>

        <div className="space-y-3">
          <h2 className="text-sm font-semibold font-mono text-slate-800 dark:text-slate-200 flex items-center gap-2">
            <Terminal className="w-4 h-4 text-cyan-500" />
            WORKSPACE NAVIGATION
          </h2>
          <div className="grid grid-cols-1 gap-2.5">
            <Button variant="secondary" className="justify-between h-11 text-xs font-mono" onClick={() => onNavigate('models')}>
              <span className="flex items-center gap-2"><Cpu className="w-4 h-4 text-cyan-500" /> Model Manager</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Button>
            <Button variant="secondary" className="justify-between h-11 text-xs font-mono" onClick={() => onNavigate('brain')}>
              <span className="flex items-center gap-2"><Brain className="w-4 h-4 text-purple-400" /> Brain & Memory</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Button>
            <Button variant="secondary" className="justify-between h-11 text-xs font-mono" onClick={() => onNavigate('web')}>
              <span className="flex items-center gap-2"><Globe className="w-4 h-4 text-emerald-400" /> Live Web Intelligence</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};
