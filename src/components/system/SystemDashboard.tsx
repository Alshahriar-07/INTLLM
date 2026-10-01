import React, { useEffect, useState } from 'react';
import {
  Activity,
  Cpu,
  HardDrive,
  Zap,
  Server,
  Database,
  Globe,
  Compass,
  WifiOff,
  CheckCircle2
} from 'lucide-react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { systemService } from '../../lib/services/systemService';
import { OllamaRuntimePanel } from './OllamaRuntimePanel';
import { useIntllm } from '../../hooks/use-intllm';

interface Telemetry {
  connected: boolean;
  cpu?: { name: string; usage: number; cores: number | null; threads?: number | null } | null;
  ram?: { usedGB: number; totalGB: number; percent: number } | null;
  gpu?: { name: string; vramUsedGB: number; vramTotalGB: number; usage: number } | null;
  disk?: { freeGB: number; totalGB: number; percent: number } | null;
  os?: Record<string, string> | null;
  services?: Record<string, any>;
  capturedAt?: string;
}

const SERVICE_ROWS = [
  { key: 'intllm', label: 'INTLLM Core', icon: Server },
  { key: 'ollama', label: 'Ollama LLM', icon: Cpu },
  { key: 'postgres', label: 'PostgreSQL', icon: Database },
  { key: 'web', label: 'Web Retrieval', icon: Globe },
  { key: 'browser', label: 'Playwright', icon: Compass }
];

export const SystemDashboard: React.FC = () => {
  const [telemetry, setTelemetry] = useState<Telemetry | null>(null);
  const [loading, setLoading] = useState(true);
  const intllm = useIntllm();

  useEffect(() => {
    let active = true;
    const load = () =>
      systemService.getSystemTelemetry().then((result) => {
        if (!active) return;
        setTelemetry((result.status as unknown as Telemetry) ?? { connected: false });
        setLoading(false);
      });
    load();
    const timer = setInterval(load, 5000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);

  const services = telemetry?.services ?? {};
  const connected = telemetry?.connected ?? false;
  const detailServices = (services?.detail as Record<string, { status?: string; detail?: string }> | undefined) ?? {};

  const gauge = (value: number | null | undefined, unit: string) =>
    value == null ? 'N/A' : `${value}${unit}`;

  return (
    <div className="flex-1 overflow-y-auto"
      >
      <div className="max-w-7xl mx-auto px-4 md:px-6 py-6 space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold font-mono tracking-tight text-primary">
              HARDWARE &amp; SYSTEM MONITOR
            </h1>
            <Badge variant="outline">SYSTEM TELEMETRY</Badge>
          </div>
          <p className="text-xs text-secondary mt-1">
            Live local hardware resource gauges and service daemon state.
          </p>
        </div>
        <div
          className={`flex items-center gap-2 text-xs font-mono px-3 py-1.5 rounded border ${
            connected
              ? 'text-success bg-success/10 border-success/25'
              : 'text-warning bg-warning/10 border-warning/25'
          }`}
        >
          {connected ? <CheckCircle2 className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
          {loading ? 'Querying telemetry…' : connected ? 'Telemetry Live' : 'Telemetry Unavailable'}
        </div>
      </div>

      {/* OLLAMA RUNTIME — real daemon control */}
      <OllamaRuntimePanel />

      {/* Service matrix */}
      <Card className="p-4 space-y-3 bg-surface border-border">
        <div className="text-xs font-mono font-semibold text-primary">
          SERVICE DAEMON STATUS MATRIX
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          {SERVICE_ROWS.map((row) => {
            const detail = detailServices[row.key];
            const up = detail
              ? detail.status === 'connected'
              : Boolean(services[row.key]);
            const Icon = row.icon;
            return (
              <div
                key={row.key}
                className="p-2.5 bg-panel-hover border border-border rounded flex items-center justify-between font-mono text-xs"
                title={detail?.detail ?? undefined}
              >
                <span className="flex items-center gap-1.5 text-secondary">
                  <Icon className="w-3.5 h-3.5" /> {row.label}
                </span>
                <Badge variant={up ? 'emerald' : 'outline'} size="sm">
                  {up ? 'Online' : 'Offline'}
                </Badge>
              </div>
            );
          })}
        </div>
      </Card>

      {/* Gauges — N/A when the backend reports no value */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="space-y-2">
          <span className="text-xs font-mono text-muted flex items-center gap-1.5">
            <Cpu className="w-4 h-4 text-muted" /> CPU Load
          </span>
          <div className="text-xl font-bold font-mono text-primary">
            {telemetry?.cpu ? `${telemetry.cpu.usage.toFixed(1)}%` : gauge(undefined, '')}
          </div>
          <span className="text-[10px] text-muted font-mono truncate">
            {telemetry?.cpu?.name ?? 'N/A'}
          </span>
        </Card>

        <Card className="space-y-2">
          <span className="text-xs font-mono text-muted flex items-center gap-1.5">
            <Server className="w-4 h-4 text-muted" /> System RAM
          </span>
          <div className="text-xl font-bold font-mono text-primary">
            {telemetry?.ram ? `${telemetry.ram.usedGB} / ${telemetry.ram.totalGB} GB` : 'N/A'}
          </div>
          <span className="text-[10px] text-muted font-mono">
            {telemetry?.ram ? `${telemetry.ram.percent.toFixed(1)}% used` : 'N/A'}
          </span>
        </Card>

        <Card className="space-y-2">
          <span className="text-xs font-mono text-muted flex items-center gap-1.5">
            <Zap className="w-4 h-4 text-muted" /> GPU VRAM
          </span>
          <div className="text-xl font-bold font-mono text-primary">
            {telemetry?.gpu
              ? `${telemetry.gpu.vramUsedGB} / ${telemetry.gpu.vramTotalGB} GB`
              : 'N/A'}
          </div>
          <span className="text-[10px] text-muted font-mono truncate">
            {telemetry?.gpu?.name ?? 'N/A'}
          </span>
        </Card>

        <Card className="space-y-2">
          <span className="text-xs font-mono text-muted flex items-center gap-1.5">
            <HardDrive className="w-4 h-4 text-muted" /> Storage
          </span>
          <div className="text-xl font-bold font-mono text-primary">
            {telemetry?.disk ? `${telemetry.disk.freeGB} GB free` : 'N/A'}
          </div>
          <span className="text-[10px] text-muted font-mono">
            {telemetry?.disk ? `of ${telemetry.disk.totalGB} GB` : 'N/A'}
          </span>
        </Card>
      </div>

      {/* Runtime versions & software inventory */}
      <Card className="p-4 space-y-3 border-border">
        <div className="text-xs font-mono font-semibold text-primary">
          RUNTIME VERSIONS
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs font-mono">
          <div className="p-2.5 bg-panel-hover border border-border rounded space-y-0.5">
            <div className="text-[10px] text-muted">INTLLM</div>
            <div className="text-primary">
              {intllm.version ? `v${intllm.version}` : 'N/A'}
            </div>
          </div>
          <div className="p-2.5 bg-panel-hover border border-border rounded space-y-0.5">
            <div className="text-[10px] text-muted">Ollama</div>
            <div className="text-primary">
              {intllm.ollama?.status === 'running' && intllm.ollama.version
                ? `v${intllm.ollama.version}`
                : 'N/A'}
            </div>
          </div>
          <div className="p-2.5 bg-panel-hover border border-border rounded space-y-0.5">
            <div className="text-[10px] text-muted">Python / OS</div>
            <div className="text-primary truncate">
              {telemetry?.os?.python
                ? `Python ${telemetry.os.python}`
                : telemetry?.os?.system
                  ? String(telemetry.os.system)
                  : 'N/A'}
            </div>
          </div>
          <div className="p-2.5 bg-panel-hover border border-border rounded space-y-0.5">
            <div className="text-[10px] text-muted">Installed Models</div>
            <div className="text-primary">
              {intllm.ollama?.status === 'running' ? intllm.ollama.modelCount ?? 'N/A' : 'N/A'}
            </div>
          </div>
        </div>
      </Card>

      {/* Process table */}
      <Card className="p-8 text-center space-y-2 border-border">
        <Activity className="w-8 h-8 text-muted mx-auto" />
        <h3 className="text-sm font-bold font-mono text-primary">
          No process telemetry
        </h3>
        <p className="text-xs text-secondary font-sans max-w-sm mx-auto">
          Per-process VRAM and thread allocation is not exposed by the current backend.
        </p>
      </Card>
    </div>
    </div>
  );
};
