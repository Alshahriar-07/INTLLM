import React, { useEffect, useState } from 'react';
import { Key, Terminal, Play, WifiOff, Plus, Trash2, Copy } from 'lucide-react';
import { ApiKey } from '../../types';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Textarea } from '../ui/Textarea';
import { Button } from '../ui/Button';
import { Tabs } from '../ui/Tabs';
import { Modal } from '../ui/Modal';
import { Input } from '../ui/Input';
import { apiService } from '../../lib/services/apiService';
import { chatService } from '../../lib/services/chatService';

export const ApiDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'keys' | 'playground'>('keys');
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [connected, setConnected] = useState(false);
  const [baseUrl, setBaseUrl] = useState('http://127.0.0.1:8000/v1');
  const [error, setError] = useState<string | undefined>();

  const [showCreate, setShowCreate] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [createdSecret, setCreatedSecret] = useState<string | null>(null);

  const [pgUser, setPgUser] = useState('Write a Python vector similarity function.');
  const [pgResponse, setPgResponse] = useState('');
  const [streaming, setStreaming] = useState(false);

  const load = async () => {
    const result = await apiService.getApiStatus();
    setKeys(result.keys);
    setConnected(result.connected);
    setBaseUrl(result.baseUrl);
    setError(result.error);
  };

  useEffect(() => {
    load();
  }, []);

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

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto overflow-y-auto max-h-[calc(100vh-3.5rem)]">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-[#21262D] pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold font-mono tracking-tight text-slate-900 dark:text-slate-100">
              LOCAL OPENAI-COMPATIBLE API
            </h1>
            <Badge variant="outline">REST / HTTP</Badge>
          </div>
          <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
            OpenAI-compatible REST endpoint at <span className="font-mono">{baseUrl}</span>
          </p>
        </div>
        <div
          className={`flex items-center gap-2 text-xs font-mono px-3 py-1.5 rounded border ${
            connected
              ? 'text-emerald-500 dark:text-emerald-400 bg-emerald-950/20 border-emerald-800/40'
              : 'text-amber-500 dark:text-amber-400 bg-amber-950/30 border-amber-800/40'
          }`}
        >
          {connected ? <Key className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
          {connected ? 'API Server Connected' : 'API Server Not Connected'}
        </div>
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
          <div className="flex justify-end">
            <Button variant="primary" size="sm" onClick={() => setShowCreate(true)} disabled={!connected}>
              <Plus className="w-3.5 h-3.5 mr-1.5" /> Create API Key
            </Button>
          </div>

          {keys.length > 0 ? (
            <div className="space-y-2">
              {keys.map((key) => (
                <Card key={key.id} className="p-3 flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm text-slate-800 dark:text-slate-100">{key.name}</span>
                      <Badge variant={key.status === 'active' ? 'emerald' : 'rose'} size="sm">{key.status}</Badge>
                    </div>
                    <div className="text-[11px] font-mono text-slate-500">
                      {key.key} · scopes: {key.scopes.join(', ')} · created {key.created.slice(0, 10)}
                      {key.lastUsed ? ` · last used ${key.lastUsed.slice(0, 10)}` : ''}
                    </div>
                  </div>
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
                </Card>
              ))}
            </div>
          ) : (
            <Card className="p-12 text-center space-y-3 border-slate-200 dark:border-[#21262D]">
              <div className="p-3 rounded-full bg-slate-200 dark:bg-slate-800/50 w-fit mx-auto text-slate-400">
                <Key className="w-8 h-8 text-slate-500" />
              </div>
              <div className="space-y-1">
                <h2 className="text-base font-bold font-mono text-slate-800 dark:text-slate-200">No API keys</h2>
                <p className="text-xs text-slate-600 dark:text-slate-400 font-sans max-w-sm mx-auto">
                  {error ?? 'Create a key to authenticate OpenAI-compatible clients.'}
                </p>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* Playground Tab */}
      {activeTab === 'playground' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card className="p-4 space-y-4 border-slate-200 dark:border-[#21262D]">
            <h3 className="text-xs font-mono font-semibold text-slate-500 flex items-center gap-1.5">
              <Terminal className="w-4 h-4" /> POST /v1/chat/completions
            </h3>
            <div className="space-y-1.5">
              <label className="text-xs font-mono text-slate-600 dark:text-slate-300">User Prompt</label>
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

          <Card className="p-4 space-y-3 border-slate-200 dark:border-[#21262D] bg-slate-50 dark:bg-[#07090C]">
            <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-2">
              <span className="text-xs font-mono font-semibold text-emerald-500">
                {pgResponse ? '200 OK' : 'Awaiting request'}
              </span>
              <span className="text-[10px] font-mono text-slate-500">Content-Type: text/event-stream</span>
            </div>
            <pre className="text-xs font-mono text-slate-700 dark:text-slate-300 overflow-x-auto p-3 bg-white dark:bg-[#0D1117] rounded border border-slate-200 dark:border-slate-800 min-h-[120px] whitespace-pre-wrap">
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
        <div className="flex items-center gap-2 p-3 rounded bg-slate-100 dark:bg-[#161B22] border border-slate-200 dark:border-slate-800">
          <code className="flex-1 text-xs font-mono break-all text-slate-800 dark:text-slate-100">
            {createdSecret}
          </code>
          <Button
            variant="outline"
            size="sm"
            onClick={() => createdSecret && navigator.clipboard?.writeText(createdSecret)}
            aria-label="Copy key"
          >
            <Copy className="w-3.5 h-3.5" />
          </Button>
        </div>
      </Modal>
    </div>
  );
};
