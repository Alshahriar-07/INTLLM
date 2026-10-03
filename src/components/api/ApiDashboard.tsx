import React, { useCallback, useEffect, useState } from 'react';
import { Key, Terminal, Play, WifiOff, Plus, Trash2, Copy, RefreshCw, Network, RotateCcw, ShieldAlert } from 'lucide-react';
import { ApiKey } from '../../types';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Textarea } from '../ui/Textarea';
import { Button } from '../ui/Button';
import { Tabs } from '../ui/Tabs';
import { Modal } from '../ui/Modal';
import { Input } from '../ui/Input';
import { apiService, ApiAccessMode, ApiServerStatus } from '../../lib/services/apiService';
import { chatService } from '../../lib/services/chatService';

const STATE_LABEL: Record<ApiServerStatus['state'], string> = {
  starting: 'API Server Starting',
  running: 'API Server Running',
  stopped: 'API Server Stopped',
  error: 'API Server Error',
  restarting: 'API Server Restarting'
};

export const ApiDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'keys' | 'playground'>('keys');
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [server, setServer] = useState<ApiServerStatus | null>(null);
  const [connected, setConnected] = useState(false);
  const [keyStoreAvailable, setKeyStoreAvailable] = useState(false);
  const [baseUrl, setBaseUrl] = useState('http://127.0.0.1:8000/v1');
  const [error, setError] = useState<string | undefined>();
  const [accessBusy, setAccessBusy] = useState(false);

  const [showCreate, setShowCreate] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [createdSecret, setCreatedSecret] = useState<string | null>(null);

  const [pgUser, setPgUser] = useState('Write a Python vector similarity function.');
  const [pgResponse, setPgResponse] = useState('');
  const [streaming, setStreaming] = useState(false);

  const load = useCallback(async () => {
    const result = await apiService.getApiStatus();
    setKeys(result.keys);
    setServer(result.server);
    setConnected(result.connected);
    setKeyStoreAvailable(result.keyStoreAvailable);
    setBaseUrl(result.baseUrl);
    setError(result.error);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const changeAccess = async (mode: ApiAccessMode) => {
    setAccessBusy(true);
    const updated = await apiService.setAccessMode(mode);
    setAccessBusy(false);
    if (updated) setServer(updated);
    await load();
  };

  const createKey = async () => {
    if (!newKeyName.trim()) return;
    const created = await apiService.createKey(newKeyName.trim(), ['chat', 'models.read']);
    if (created) {
      setCreatedSecret(created.secret);
      setNewKeyName('');
      setShowCreate(false);
      await load();
    }
  };

  const regenerateKey = async (id: string) => {
    const created = await apiService.regenerateKey(id);
    if (created) {
      setCreatedSecret(created.secret);
      await load();
    }
  };

  const runPlayground = () => {
    setPgResponse('');
    setStreaming(true);
    chatService.stream(
      { messages: [{ role: 'user', content: pgUser }], use_brain: true },
      {
        onDelta: (content) => setPgResponse((prev) => prev + content),
        onError: (message) => {
          setPgResponse(JSON.stringify({ error: { message, type: 'service_unavailable' } }, null, 2));
          setStreaming(false);
        },
        onCompleted: () => setStreaming(false)
      }
    );
  };

  const state = server?.state ?? (connected ? 'running' : 'stopped');
  const stateTone =
    state === 'running'
      ? 'text-success bg-success/10 border-success/25'
      : state === 'error'
        ? 'text-error bg-error/10 border-error/25'
        : 'text-warning bg-warning/10 border-warning/25';

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-7xl mx-auto px-4 md:px-6 py-6 space-y-5">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold font-mono tracking-tight text-primary">
                LOCAL OPENAI-COMPATIBLE API
              </h1>
              <Badge variant="outline">REST / HTTP</Badge>
            </div>
            <p className="text-xs text-secondary mt-1">
              OpenAI-compatible REST endpoint at <span className="font-mono">{baseUrl}</span>
            </p>
          </div>
          <div className={`flex items-center gap-2 text-xs font-mono px-3 py-1.5 rounded border ${stateTone}`}>
            {state === 'running' ? <Key className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
            {STATE_LABEL[state as ApiServerStatus['state']] ?? 'API Server Unknown'}
            <Button
              variant="ghost"
              size="icon"
              onClick={load}
              title="Refresh API status"
              aria-label="Refresh API status"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>

        {/* Access + endpoints */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card className="p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-semibold text-primary flex items-center gap-1.5">
                <Network className="w-4 h-4 text-accent" /> ACCESS MODE
              </span>
              {server?.requiresRestart && (
                <Badge variant="amber" size="sm">restart required</Badge>
              )}
            </div>
            <div className="grid grid-cols-2 gap-2">
              {(['local', 'lan'] as const).map((mode) => {
                const active = (server?.accessMode ?? 'local') === mode;
                return (
                  <button
                    key={mode}
                    type="button"
                    disabled={accessBusy || !keyStoreAvailable}
                    onClick={() => changeAccess(mode)}
                    className={`p-3 rounded border text-left transition-colors ${
                      active
                        ? 'border-accent/40 bg-accent/[0.06]'
                        : 'border-border bg-panel hover:bg-panel-hover'
                    }`}
                  >
                    <div className="text-xs font-mono font-semibold text-primary">
                      {mode === 'local' ? 'LOCAL ONLY' : 'LAN ACCESS'}
                    </div>
                    <div className="text-[11px] text-secondary font-sans mt-0.5">
                      {mode === 'local'
                        ? '127.0.0.1 only — safest default'
                        : 'Reachable from the same network; API key required'}
                    </div>
                  </button>
                );
              })}
            </div>
            {server?.requiresRestart && (
              <p className="text-[11px] text-warning font-sans">
                Restart INTLLM to apply {server.storedAccessMode === 'lan' ? 'LAN' : 'Local'} access.
              </p>
            )}
            <p className="text-[11px] text-muted font-sans">
              LAN access stays OFF by default. Internal management endpoints are never
              exposed to the network — only the authenticated API below.
            </p>
          </Card>

          <Card className="p-4 space-y-2">
            <span className="text-xs font-mono font-semibold text-primary">ENDPOINTS</span>
            <div className="space-y-1.5 text-[11px] font-mono">
              <div className="flex items-center justify-between gap-2">
                <span className="text-muted">Local</span>
                <span className="text-primary truncate">{server?.localBaseUrl ?? baseUrl}</span>
              </div>
              <div className="flex items-center justify-between gap-2">
                <span className="text-muted">LAN</span>
                <span className={server?.lanBaseUrl ? 'text-primary truncate' : 'text-muted'}>
                  {server?.lanEnabled
                    ? server.lanBaseUrl ?? 'no LAN address detected'
                    : 'disabled (Local Only)'}
                </span>
              </div>
              <div className="flex items-center justify-between gap-2">
                <span className="text-muted">Ollama</span>
                <span className="text-primary">{server?.ollama?.status ?? 'unknown'}</span>
              </div>
              <div className="flex items-center justify-between gap-2">
                <span className="text-muted">Keys</span>
                <span className="text-primary">
                  {server ? `${server.keyCount} active` : 'unknown'}
                </span>
              </div>
            </div>
            {server?.detail && (
              <p className="text-[11px] text-secondary font-sans">{server.detail}</p>
            )}
          </Card>
        </div>

        {/* Tabs */}
        <Tabs
          tabs={[
            { id: 'keys', label: 'API Keys Management', icon: <Key className="w-4 h-4" /> },
            { id: 'playground', label: 'API Playground', icon: <Play className="w-4 h-4" /> }
          ]}
          activeTab={activeTab}
          onChange={(tab) => setActiveTab(tab as 'keys' | 'playground')}
        />

        {/* API Keys Tab */}
        {activeTab === 'keys' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between gap-3">
              {!keyStoreAvailable && (
                <span className="text-[11px] font-mono text-warning">
                  Key store unavailable — PostgreSQL must be running to manage keys.
                </span>
              )}
              <div className="ml-auto">
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => setShowCreate(true)}
                  disabled={!keyStoreAvailable}
                >
                  <Plus className="w-3.5 h-3.5 mr-1.5" /> Generate API Key
                </Button>
              </div>
            </div>

            {keys.length > 0 ? (
              <div className="space-y-2">
                {keys.map((key) => (
                  <Card key={key.id} className="p-3 flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-sm text-primary">{key.name}</span>
                        <Badge variant={key.status === 'active' ? 'emerald' : 'rose'} size="sm">
                          {key.status}
                        </Badge>
                      </div>
                      <div className="text-[11px] font-mono text-muted">
                        {key.key} · scopes: {key.scopes.join(', ')} · created {key.created.slice(0, 10)}
                        {key.lastUsed ? ` · last used ${key.lastUsed.slice(0, 10)}` : ''}
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      {key.status === 'active' && (
                        <Button
                          variant="outline"
                          size="sm"
                          aria-label={`Regenerate ${key.name}`}
                          title="Regenerate (revokes the old key)"
                          onClick={() => regenerateKey(key.id)}
                        >
                          <RotateCcw className="w-3.5 h-3.5" />
                        </Button>
                      )}
                      <Button
                        variant="danger"
                        size="sm"
                        aria-label={`Revoke ${key.name}`}
                        onClick={async () => {
                          await apiService.revokeKey(key.id);
                          await load();
                        }}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </Button>
                    </div>
                  </Card>
                ))}
              </div>
            ) : (
              <Card className="p-12 text-center space-y-3 border-border">
                <div className="p-3 rounded-full bg-panel-hover w-fit mx-auto text-muted">
                  <Key className="w-8 h-8 text-muted" />
                </div>
                <div className="space-y-1">
                  <h2 className="text-base font-bold font-mono text-primary">No API keys</h2>
                  <p className="text-xs text-secondary font-sans max-w-sm mx-auto">
                    {error ?? 'Generate a key to authenticate OpenAI-compatible clients.'}
                  </p>
                </div>
              </Card>
            )}
          </div>
        )}

        {/* Playground Tab */}
        {activeTab === 'playground' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="p-4 space-y-4 border-border">
              <h3 className="text-xs font-mono font-semibold text-muted flex items-center gap-1.5">
                <Terminal className="w-4 h-4" /> POST /v1/chat/completions
              </h3>
              <div className="space-y-1.5">
                <label className="text-xs font-mono text-secondary">User Prompt</label>
                <Textarea
                  value={pgUser}
                  onChange={(e) => setPgUser(e.target.value)}
                  rows={4}
                  className="font-mono text-xs"
                />
              </div>
              <Button
                variant="primary"
                className="w-full font-mono text-xs h-9"
                onClick={runPlayground}
                disabled={!connected || streaming || !pgUser.trim()}
              >
                {streaming ? 'Streaming…' : connected ? 'Send API Request' : 'Server Disconnected'}
              </Button>
            </Card>

            <Card className="p-4 space-y-3 border-border bg-canvas">
              <div className="flex items-center justify-between border-b border-border pb-2">
                <span className="text-xs font-mono font-semibold text-success">
                  {pgResponse ? '200 OK' : 'Awaiting request'}
                </span>
                <span className="text-[10px] font-mono text-muted">Content-Type: text/event-stream</span>
              </div>
              <pre className="text-xs font-mono text-primary overflow-x-auto p-3 bg-surface rounded border border-border min-h-[120px] whitespace-pre-wrap">
                <code>{pgResponse || '// Response stream appears here'}</code>
              </pre>
            </Card>
          </div>
        )}

        {/* Create key modal */}
        <Modal
          isOpen={showCreate}
          onClose={() => setShowCreate(false)}
          title="Create API Key"
          description="The raw key is shown once. Store it securely."
          footer={
            <>
              <Button variant="ghost" onClick={() => setShowCreate(false)}>Cancel</Button>
              <Button variant="primary" onClick={createKey} disabled={!newKeyName.trim()}>
                Generate
              </Button>
            </>
          }
        >
          <Input
            value={newKeyName}
            onChange={(e) => setNewKeyName(e.target.value)}
            placeholder="Key name (e.g. claude-code)"
            className="font-mono text-sm"
          />
        </Modal>

        {/* Secret reveal modal */}
        <Modal
          isOpen={createdSecret !== null}
          onClose={() => setCreatedSecret(null)}
          title="API Key Created"
          description="Copy this key now — it will not be shown again."
          footer={<Button variant="primary" onClick={() => setCreatedSecret(null)}>Done</Button>}
        >
          <div className="space-y-3">
            <div className="flex items-center gap-2 p-3 rounded bg-panel-hover border border-border">
              <code className="flex-1 text-xs font-mono break-all text-primary">{createdSecret}</code>
              <Button
                variant="outline"
                size="sm"
                onClick={() => createdSecret && navigator.clipboard?.writeText(createdSecret)}
                aria-label="Copy key"
              >
                <Copy className="w-3.5 h-3.5" />
              </Button>
            </div>
            <p className="flex items-start gap-1.5 text-[11px] text-warning font-sans">
              <ShieldAlert className="w-3.5 h-3.5 mt-0.5 shrink-0" />
              Keep this key secret. INTLLM stores only a hash and cannot show it again. Never
              commit it to source control.
            </p>
          </div>
        </Modal>
      </div>
    </div>
  );
};
