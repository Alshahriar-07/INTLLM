import React, { useCallback, useEffect, useState } from 'react';
import { Brain, Layers, WifiOff, RefreshCw, Search, Database } from 'lucide-react';
import { MemoryItem } from '../../types';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Input } from '../ui/Input';
import { Button } from '../ui/Button';
import { BrainStats, brainService } from '../../lib/services/brainService';
import { useIntllm } from '../../hooks/use-intllm';

export const BrainDashboard: React.FC = () => {
  const intllm = useIntllm();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedLayer, setSelectedLayer] = useState<'ALL' | 'L0' | 'L1' | 'L2'>('ALL');
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [stats, setStats] = useState<BrainStats | null>(null);
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | undefined>();

  const load = useCallback(async (query?: string) => {
    setLoading(true);
    const layer = selectedLayer === 'ALL' ? undefined : selectedLayer;
    const result = query
      ? await brainService.searchMemories(query)
      : await brainService.getBrainMemories({ layer });
    setMemories(result.memories);
    setStats(result.stats);
    setConnected(result.connected);
    setError(result.error);
    setLoading(false);
  }, [selectedLayer]);

  useEffect(() => {
    load();
  }, [load]);

  const onSearch = (event: React.FormEvent) => {
    event.preventDefault();
    load(searchQuery.trim() || undefined);
  };

  // Prefer the backend's real memory readiness (PostgreSQL + pgvector + schema)
  // over inferring ``unavailable`` from a single failed fetch.
  const memoryService = intllm.services?.memory;
  const memoryReady = memoryService ? memoryService.status === 'connected' : connected;
  const memoryLabel = memoryService
    ? memoryService.status === 'connected'
      ? 'PostgreSQL Connected'
      : memoryService.status === 'degraded'
        ? 'Memory degraded'
        : 'Memory store unavailable'
    : connected
      ? 'PostgreSQL Connected'
      : 'PostgreSQL Service Offline';

  return (
    <div className="flex-1 overflow-y-auto"
      >
      <div className="max-w-7xl mx-auto px-4 md:px-6 py-6 space-y-5">
      {/* Title Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold font-mono tracking-tight text-primary">
              LAYERED BRAIN DASHBOARD
            </h1>
            <Badge variant="outline">L0 / L1 / L2 MEMORY</Badge>
          </div>
          <p className="text-xs text-secondary mt-1">
            Local vector memory: in-memory routing micro-index (L0), fast hot cache (L1), and
            persistent PostgreSQL pgvector storage (L2).
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            className="font-mono text-xs"
            onClick={() => load(searchQuery.trim() || undefined)}
            disabled={loading}
          >
            <RefreshCw className="w-3.5 h-3.5 mr-1" /> Refresh
          </Button>
        </div>
      </div>

      {/* Layer Architecture */}
      <Card className="p-4 space-y-3 bg-surface">
        <div className="text-xs font-mono font-semibold text-primary flex items-center justify-between">
          <span className="flex items-center gap-1.5">
            <Layers className="w-4 h-4 text-accent" /> THREE-LAYER ROUTING ARCHITECTURE
          </span>
          <span className="text-muted text-[11px]">L0 → L1 → L2 → Live Web</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs font-mono">
          <div className="p-3 rounded border border-accent/30 bg-accent/[0.04] space-y-1">
            <div className="flex items-center justify-between font-bold text-accent">
              <span>L0 FLASH BRAIN</span>
              <Badge variant="outline" size="sm">Fast</Badge>
            </div>
            <p className="text-[11px] text-secondary font-sans">
              In-memory micro vector index for rapid routing.
            </p>
          </div>
          <div className="p-3 rounded border border-border bg-panel space-y-1">
            <div className="flex items-center justify-between font-bold text-primary">
              <span>L1 HOT CACHE</span>
              <Badge variant="outline" size="sm">Cache</Badge>
            </div>
            <p className="text-[11px] text-secondary font-sans">
              High-frequency compact knowledge promoted to fast storage.
            </p>
          </div>
          <div className="p-3 rounded border border-border bg-panel space-y-1">
            <div className="flex items-center justify-between font-bold text-primary">
              <span>L2 SECONDARY BRAIN</span>
              <Badge variant="outline" size="sm">PostgreSQL</Badge>
            </div>
            <p className="text-[11px] text-secondary font-sans">
              Persistent vector storage in PostgreSQL + pgvector.
            </p>
          </div>
          <div className="p-3 rounded border border-success/25 bg-success/5 space-y-1">
            <div className="flex items-center justify-between font-bold text-success">
              <span>LIVE WEB RETRIEVAL</span>
              <Badge variant="outline" size="sm">Fallback</Badge>
            </div>
            <p className="text-[11px] text-secondary font-sans">
              Triggered when memory confidence is low.
            </p>
          </div>
        </div>
      </Card>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="space-y-1">
          <span className="text-xs font-mono text-muted">Total Memories Stored</span>
          <div className="text-2xl font-bold font-mono text-primary">
            {stats ? stats.totalMemories : '--'}
          </div>
          <span className="text-[10px] text-muted font-mono">
            {stats
              ? `L0: ${stats.byLayer?.L0 ?? 0} | L1: ${stats.byLayer?.L1 ?? 0} | L2: ${stats.byLayer?.L2 ?? 0}`
              : 'Memory service offline'}
          </span>
        </Card>
        <Card className="space-y-1">
          <span className="text-xs font-mono text-muted">Flash Brain Hit Rate</span>
          <div className="text-2xl font-bold font-mono text-primary">
            {stats?.hitRatePercent != null ? `${stats.hitRatePercent}%` : '--'}
          </div>
          <span className="text-[10px] text-muted font-mono">From measured lookups</span>
        </Card>
        <Card className="space-y-1">
          <span className="text-xs font-mono text-muted">Avg Lookup Latency</span>
          <div className="text-2xl font-bold font-mono text-primary">
            {stats?.avgLookupTimeMs != null ? `${stats.avgLookupTimeMs} ms` : '-- ms'}
          </div>
          <span className="text-[10px] text-muted font-mono">No telemetry data</span>
        </Card>
        <Card className="space-y-1">
          <span className="text-xs font-mono text-muted">Knowledge Freshness</span>
          <div className="text-2xl font-bold font-mono text-primary">
            {stats?.freshnessPercent != null ? `${stats.freshnessPercent}%` : '-- %'}
          </div>
          <span className="text-[10px] text-muted font-mono">
            {connected ? 'Computed from stored TTL' : 'Connect database engine'}
          </span>
        </Card>
      </div>

      {/* Search & Filter Controls */}
      <form onSubmit={onSearch} className="flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-96">
          <Search className="w-4 h-4 text-muted absolute left-3 top-1/2 -translate-y-1/2" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search memory titles & content…"
            className="pl-9 font-mono text-xs"
            disabled={!connected}
          />
        </div>

        <div className="flex items-center gap-1.5 w-full sm:w-auto overflow-x-auto">
          {(['ALL', 'L0', 'L1', 'L2'] as const).map((layer) => (
            <button
              key={layer}
              type="button"
              onClick={() => setSelectedLayer(layer)}
              className={`px-3 py-1 rounded text-xs font-mono transition-colors border ${
                selectedLayer === layer
                  ? 'bg-accent/10 text-accent border-accent/30 font-semibold'
                  : 'bg-panel-hover text-muted border-border'
              }`}
            >
              {layer === 'ALL' ? 'All Layers' : layer}
            </button>
          ))}
        </div>
      </form>

      {/* Memory Records / Empty State */}
      {memories.length > 0 ? (
        <div className="space-y-2">
          {memories.map((memory) => (
            <Card key={memory.id} className="p-3 space-y-1.5 border-border">
              <div className="flex items-center justify-between gap-2">
                <h3 className="text-sm font-semibold font-mono text-primary truncate">
                  {memory.title}
                </h3>
                <div className="flex items-center gap-1.5 shrink-0">
                  <Badge variant="cyan" size="sm">{memory.layer}</Badge>
                  <Badge variant="outline" size="sm">{memory.type}</Badge>
                  <Badge variant="outline" size="sm">{memory.status}</Badge>
                </div>
              </div>
              <p className="text-xs text-secondary font-sans line-clamp-2">
                {memory.rawSnippet}
              </p>
              <div className="flex items-center gap-3 text-[10px] font-mono text-muted">
                <span>Confidence {Math.round(memory.confidence)}%</span>
                <span>Freshness {Math.round(memory.freshnessScore)}%</span>
                <span className="truncate max-w-[240px]">{memory.source}</span>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <Card className="p-8 text-center space-y-3 border-border">
          <div className="p-3 rounded-full bg-panel-hover w-fit mx-auto text-muted">
            <Brain className="w-8 h-8 text-muted" />
          </div>
          <div className="space-y-1">
            <h3 className="text-sm font-bold font-mono text-primary">
              {loading ? 'Loading memories…' : memoryReady ? 'No memories available' : 'Memory store unavailable'}
            </h3>
            <p className="text-xs text-secondary font-sans max-w-sm mx-auto">
              {error ??
                'Memory data appears when the runtime and PostgreSQL pgvector database are connected.'}
            </p>
          </div>
          <div className="pt-2">
            <Badge variant="outline" size="sm">
              {memoryReady ? <Database className="w-3 h-3 mr-1" /> : <WifiOff className="w-3 h-3 mr-1" />}
              {memoryLabel}
            </Badge>
          </div>
        </Card>
      )}
    </div>
    </div>
  );
};
