import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Cpu,
  WifiOff,
  Server,
  CheckCircle2,
  Download,
  Trash2,
  Star,
  Loader2,
  AlertTriangle
} from 'lucide-react';
import { HardwareTier, Model } from '../../types';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { Modal } from '../ui/Modal';
import { Input } from '../ui/Input';
import { Progress } from '../ui/Progress';
import { modelService } from '../../lib/services/modelService';
import { useIntllm } from '../../hooks/use-intllm';

interface PullState {
  name: string;
  progress: number;
  status: string;
  failed: boolean;
}

export const ModelManager: React.FC = () => {
  const { setCurrentModel, refresh: refreshGlobal } = useIntllm();
  const [activeTier, setActiveTier] = useState<HardwareTier | 'ALL'>('ALL');
  const [models, setModels] = useState<Model[]>([]);
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | undefined>();

  const [showPull, setShowPull] = useState(false);
  const [pullName, setPullName] = useState('');
  const [pull, setPull] = useState<PullState | null>(null);
  const [busyModel, setBusyModel] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const result = await modelService.getInstalledModels();
    setModels(result.models);
    setConnected(result.connected);
    setError(result.error);
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const filtered = useMemo(
    () => (activeTier === 'ALL' ? models : models.filter((m) => m.tier === activeTier)),
    [models, activeTier]
  );

  const startPull = () => {
    const name = pullName.trim();
    if (!name || pull) return;
    setActionError(null);
    setPull({ name, progress: 0, status: 'Starting…', failed: false });
    setShowPull(false);
    modelService.pull(
      name,
      (data) => {
        setPull((prev) =>
          prev
            ? {
                ...prev,
                progress:
                  data?.total && data?.completed
                    ? Math.round((Number(data.completed) / Number(data.total)) * 100)
                    : prev.progress,
                status: String(data?.status ?? prev.status)
              }
            : prev
        );
      },
      (message) => {
        setPull((prev) => (prev ? { ...prev, failed: true, status: message } : prev));
      }
    );
  };

  const onDefault = async (name: string) => {
    setBusyModel(name);
    setActionError(null);
    const ok = await modelService.setDefault(name);
    if (!ok) setActionError(`Could not set default model: ${name}`);
    else {
      setCurrentModel(name);
      await load();
      await refreshGlobal();
    }
    setBusyModel(null);
  };

  const onDelete = async (name: string) => {
    if (!window.confirm(`Delete model "${name}" from Ollama? This cannot be undone.`)) return;
    setBusyModel(name);
    setActionError(null);
    const ok = await modelService.deleteModel(name);
    if (!ok) setActionError(`Could not delete model: ${name}`);
    else {
      await load();
      await refreshGlobal();
    }
    setBusyModel(null);
  };

  return (
    <div className="flex-1 overflow-y-auto"
      >
      <div className="max-w-7xl mx-auto px-4 md:px-6 py-6 space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold font-mono tracking-tight text-primary">
              MODEL MANAGER
            </h1>
            <Badge variant="outline">OLLAMA REGISTRY</Badge>
          </div>
          <p className="text-xs text-secondary mt-1">
            Hardware-aware LLM registry backed by the actual Ollama inventory on this machine.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="primary"
            size="sm"
            onClick={() => setShowPull(true)}
            disabled={!connected}
            title={connected ? 'Pull a model into Ollama' : 'Connect to Ollama first'}
          >
            <Download className="w-3.5 h-3.5" /> Pull a Model
          </Button>
          <div
            className={`flex items-center gap-2 text-xs font-mono px-3 py-1.5 rounded border ${
              connected
                ? 'text-success bg-success/10 border-success/25'
                : 'text-warning bg-warning/10 border-warning/25'
            }`}
          >
            {connected ? <Server className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
            {loading
              ? 'Querying Ollama…'
              : connected
                ? `${models.length} models installed`
                : 'Model Registry Offline'}
          </div>
        </div>
      </div>

      {/* Real action error */}
      {actionError && (
        <div className="flex items-center gap-2 p-2.5 rounded bg-error/5 border border-error/25 text-[11px] font-mono text-error">
          <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
          {actionError}
        </div>
      )}

      {/* Active pull progress (real SSE stream) */}
      {pull && (
        <Card className="p-4 space-y-2 border-accent/30">
          <div className="flex items-center justify-between text-xs font-mono">
            <span className="flex items-center gap-2 text-primary">
              {pull.failed ? (
                <AlertTriangle className="w-4 h-4 text-error" />
              ) : (
                <Loader2 className="w-4 h-4 animate-spin text-accent" />
              )}
              ollama pull {pull.name}
            </span>
            <div className="flex items-center gap-2">
              <span className={pull.failed ? 'text-error' : 'text-accent'}>
                {pull.failed ? 'failed' : `${pull.progress}%`}
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setPull(null)}
                aria-label="Dismiss pull status"
              >
                ✕
              </Button>
            </div>
          </div>
          <Progress value={pull.progress} color={pull.failed ? 'rose' : 'cyan'} />
          <p className={`text-[11px] font-mono ${pull.failed ? 'text-error' : 'text-muted'}`}>
            {pull.status}
          </p>
        </Card>
      )}

      {/* Hardware Recommendation Tiers */}
      <Card className="p-4 bg-surface border-border space-y-3">
        <div className="text-xs font-mono font-semibold text-primary flex items-center gap-2">
          <Cpu className="w-4 h-4 text-muted" />
          HARDWARE RECOMMENDATION CATEGORIES
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <button
            onClick={() => setActiveTier(activeTier === 'POTATO' ? 'ALL' : 'POTATO')}
            className={`p-3 rounded border text-left font-mono transition-all ${
              activeTier === 'POTATO'
                ? 'bg-accent/10 border-accent/30 font-semibold'
                : 'bg-canvas border-border'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="font-bold text-warning text-xs">POTATO</span>
              <Badge variant="amber" size="sm">&lt; 3B params</Badge>
            </div>
            <p className="text-[11px] text-muted font-sans mt-1">
              Tiny models for low-end hardware &amp; integrated graphics.
            </p>
          </button>

          <button
            onClick={() => setActiveTier(activeTier === 'MEDIUM' ? 'ALL' : 'MEDIUM')}
            className={`p-3 rounded border text-left font-mono transition-all ${
              activeTier === 'MEDIUM'
                ? 'bg-accent/10 border-accent/30 font-semibold'
                : 'bg-canvas border-border'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="font-bold text-accent text-xs">MEDIUM</span>
              <Badge variant="cyan" size="sm">3B – 8B params</Badge>
            </div>
            <p className="text-[11px] text-muted font-sans mt-1">
              Balanced mid-range models for everyday hardware.
            </p>
          </button>

          <button
            onClick={() => setActiveTier(activeTier === 'HIGH' ? 'ALL' : 'HIGH')}
            className={`p-3 rounded border text-left font-mono transition-all ${
              activeTier === 'HIGH'
                ? 'bg-accent/10 border-accent/30 font-semibold'
                : 'bg-canvas border-border'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="font-bold text-success text-xs">HIGH</span>
              <Badge variant="emerald" size="sm">&ge; 8B params</Badge>
            </div>
            <p className="text-[11px] text-muted font-sans mt-1">
              Larger models for high-end desktops &amp; workstations.
            </p>
          </button>
        </div>
      </Card>

      {/* Model List / Empty State */}
      {filtered.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((model) => (
            <Card key={model.id} className="space-y-3 border-border">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <h3 className="font-bold text-sm font-mono text-primary truncate">
                    {model.name}
                  </h3>
                  <span className="text-[11px] text-muted font-mono">
                    {model.family ?? 'unknown'} · {model.parameterSize ?? 'n/a'}
                  </span>
                </div>
                {model.isDefault && (
                  <Badge variant="emerald" size="sm">
                    <CheckCircle2 className="w-3 h-3 mr-1" /> Default
                  </Badge>
                )}
              </div>
              <div className="flex flex-wrap gap-1.5 text-[10px] font-mono">
                {model.quantization && <Badge variant="outline" size="sm">{model.quantization}</Badge>}
                {model.tier && <Badge variant="cyan" size="sm">{model.tier}</Badge>}
                {model.memoryReqGB != null && (
                  <Badge variant="outline" size="sm">~{model.memoryReqGB} GB</Badge>
                )}
                {model.capabilities.slice(0, 2).map((cap) => (
                  <Badge key={cap} variant="outline" size="sm">{cap}</Badge>
                ))}
              </div>
              <div className="flex items-center gap-1.5 pt-1 border-t border-border">
                {!model.isDefault && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onDefault(model.name)}
                    disabled={busyModel === model.name}
                    title="Set as default model"
                  >
                    {busyModel === model.name ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Star className="w-3.5 h-3.5" />
                    )}
                    Set Default
                  </Button>
                )}
                <Button
                  variant="danger"
                  size="sm"
                  onClick={() => onDelete(model.name)}
                  disabled={busyModel === model.name}
                  title={`Delete ${model.name} from Ollama`}
                >
                  {busyModel === model.name ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Trash2 className="w-3.5 h-3.5" />
                  )}
                  Delete
                </Button>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <Card className="p-12 text-center space-y-3 border-border">
          <div className="p-3 rounded-full bg-panel-hover w-fit mx-auto text-muted">
            <Cpu className="w-8 h-8 text-muted" />
          </div>
          <div className="space-y-1">
            <h2 className="text-base font-bold font-mono text-primary">
              {connected ? 'No local models found.' : 'No models detected'}
            </h2>
            <p className="text-xs text-secondary font-sans max-w-sm mx-auto">
              {error ??
                'Pull a model with Ollama (e.g. `ollama pull llama3.1`) to see it here.'}
            </p>
            {connected && (
              <Button
                variant="primary"
                size="sm"
                className="mt-2"
                onClick={() => setShowPull(true)}
              >
                <Download className="w-3.5 h-3.5" /> Pull a Model
              </Button>
            )}
          </div>
        </Card>
      )}

      {/* Pull modal */}
      <Modal
        isOpen={showPull}
        onClose={() => setShowPull(false)}
        title="Pull a Model"
        description="Downloads the model into the local Ollama inventory (real ollama pull)."
        footer={
          <>
            <Button variant="ghost" onClick={() => setShowPull(false)}>
              Cancel
            </Button>
            <Button variant="primary" onClick={startPull} disabled={!pullName.trim() || pull !== null}>
              Start Pull
            </Button>
          </>
        }
      >
        <Input
          value={pullName}
          onChange={(e) => setPullName(e.target.value)}
          placeholder="e.g. llama3.1 or qwen2.5-coder:7b"
          className="font-mono text-sm"
        />
      </Modal>
    </div>
    </div>
  );
};
