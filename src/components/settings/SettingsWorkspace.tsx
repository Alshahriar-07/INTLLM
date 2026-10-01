import React, { useState } from 'react';
import { useTheme, Theme } from '../../hooks/use-theme';
import {
  API_BASE,
  CONNECTION_TIMEOUT_MS,
  INTLLM_BASE_URL,
  OLLAMA_DEFAULT_URL,
  OPENAI_BASE,
  POLLING_INTERVAL_MS
} from '../../lib/api/client';
import {
  Activity,
  Brain,
  Compass,
  Cpu,
  Globe,
  Key,
  Laptop,
  Monitor,
  Moon,
  Server,
  ShieldCheck,
  SlidersHorizontal,
  Sun,
  Wrench
} from 'lucide-react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Switch } from '../ui/Switch';
import { Button } from '../ui/Button';
import { useIntllm } from '../../hooks/use-intllm';
import { cn } from '../../lib/utils';

type SectionId =
  | 'general'
  | 'appearance'
  | 'models'
  | 'ollama'
  | 'memory'
  | 'internet'
  | 'browser'
  | 'tools'
  | 'api'
  | 'security'
  | 'advanced';

const SECTIONS: { id: SectionId; label: string; icon: React.ReactNode }[] = [
  { id: 'general', label: 'General', icon: <SlidersHorizontal className="w-4 h-4" /> },
  { id: 'appearance', label: 'Appearance', icon: <Sun className="w-4 h-4" /> },
  { id: 'models', label: 'Models', icon: <Cpu className="w-4 h-4" /> },
  { id: 'ollama', label: 'Ollama', icon: <Server className="w-4 h-4" /> },
  { id: 'memory', label: 'Memory', icon: <Brain className="w-4 h-4" /> },
  { id: 'internet', label: 'Internet', icon: <Globe className="w-4 h-4" /> },
  { id: 'browser', label: 'Browser', icon: <Compass className="w-4 h-4" /> },
  { id: 'tools', label: 'Tools', icon: <Wrench className="w-4 h-4" /> },
  { id: 'api', label: 'API', icon: <Key className="w-4 h-4" /> },
  { id: 'security', label: 'Security', icon: <ShieldCheck className="w-4 h-4" /> },
  { id: 'advanced', label: 'Advanced', icon: <Activity className="w-4 h-4" /> }
];

const THEME_OPTIONS: { value: Theme; label: string; icon: React.ReactNode }[] = [
  { value: 'light', label: 'Light', icon: <Sun className="w-4 h-4" /> },
  { value: 'dark', label: 'Dark', icon: <Moon className="w-4 h-4" /> },
  { value: 'system', label: 'System', icon: <Monitor className="w-4 h-4" /> }
];

/** A titled setting row with optional trailing control. */
const SettingRow: React.FC<{
  title: string;
  description?: string;
  children?: React.ReactNode;
  last?: boolean;
}> = ({ title, description, children, last }) => (
  <div className={cn('flex items-center justify-between gap-4 py-3', !last && 'border-b border-border')}>
    <div className="min-w-0">
      <h3 className="text-sm font-medium text-primary">{title}</h3>
      {description && <p className="text-xs text-secondary mt-0.5 leading-relaxed">{description}</p>}
    </div>
    {children && <div className="shrink-0">{children}</div>}
  </div>
);

const SectionTitle: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <h2 className="text-xs font-semibold uppercase tracking-wider text-muted mb-2">{children}</h2>
);

export const SettingsWorkspace: React.FC = () => {
  const { theme, setTheme } = useTheme();
  const intllm = useIntllm();
  const [activeSection, setActiveSection] = useState<SectionId>('general');

  // Local preference toggles (UI-level; runtime policy remains server-side).
  const [localOnly, setLocalOnly] = useState(true);
  const [telemetry, setTelemetry] = useState(false);
  const [autoOllama, setAutoOllama] = useState(true);
  const [l0Caching, setL0Caching] = useState(true);
  const [webVerification, setWebVerification] = useState(true);

  const runtimeRows: { label: string; value: string }[] = [
    { label: 'Backend URL (VITE_INTLLM_BASE_URL)', value: INTLLM_BASE_URL ?? 'not configured' },
    { label: 'API base', value: API_BASE ?? 'unavailable' },
    { label: 'OpenAI-compatible base', value: OPENAI_BASE ?? 'unavailable' },
    { label: 'Ollama URL (backend-managed)', value: OLLAMA_DEFAULT_URL },
    { label: 'Connection timeout', value: `${CONNECTION_TIMEOUT_MS} ms` },
    { label: 'Polling interval', value: `${POLLING_INTERVAL_MS} ms` }
  ];

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-5xl mx-auto px-4 md:px-6 py-6">
        {/* Header */}
        <div className="border-b border-border pb-4 mb-5">
          <h1 className="text-xl font-semibold tracking-tight text-primary">Settings</h1>
          <p className="text-xs text-secondary mt-1">
            Local runtime behavior, appearance, memory routing, and hardware limits. Preferences are stored on this
            machine only.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-[200px_1fr] gap-6">
          {/* Section navigation */}
          <nav className="space-y-0.5 md:sticky md:top-0 self-start" aria-label="Settings sections">
            {SECTIONS.map((sec) => (
              <button
                key={sec.id}
                onClick={() => setActiveSection(sec.id)}
                aria-current={activeSection === sec.id ? 'true' : undefined}
                className={cn(
                  'w-full flex items-center gap-2.5 h-8 px-2.5 rounded-md text-[13px] transition-colors text-left focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring',
                  activeSection === sec.id
                    ? 'bg-panel-hover text-primary font-medium'
                    : 'text-secondary hover:text-primary hover:bg-panel-hover'
                )}
              >
                <span className={cn(activeSection === sec.id ? 'text-accent' : 'text-muted')}>{sec.icon}</span>
                <span>{sec.label}</span>
              </button>
            ))}
          </nav>

          {/* Section content */}
          <div className="space-y-4 min-w-0">
            {/* General */}
            {activeSection === 'general' && (
              <Card className="p-4">
                <SectionTitle>General</SectionTitle>
                <SettingRow
                  title="Automatic Ollama launch"
                  description="Start the local Ollama service automatically when INTLLM opens."
                >
                  <Switch checked={autoOllama} onChange={setAutoOllama} />
                </SettingRow>
                <SettingRow
                  title="Background maintenance"
                  description="Allow low-priority memory upkeep while the runtime is idle."
                  last
                >
                  <Badge variant="outline">Managed by runtime</Badge>
                </SettingRow>
              </Card>
            )}

            {/* Appearance */}
            {activeSection === 'appearance' && (
              <Card className="p-4">
                <SectionTitle>Appearance</SectionTitle>
                <SettingRow title="Theme" description="Applied instantly and remembered on this device.">
                  <div className="flex items-center gap-1 p-0.5 rounded-md border border-border bg-canvas" role="radiogroup" aria-label="Theme">
                    {THEME_OPTIONS.map((opt) => (
                      <button
                        key={opt.value}
                        role="radio"
                        aria-checked={theme === opt.value}
                        onClick={() => setTheme(opt.value)}
                        className={cn(
                          'flex items-center gap-1.5 h-7 px-2.5 rounded text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring',
                          theme === opt.value
                            ? 'bg-panel-hover text-primary'
                            : 'text-muted hover:text-primary'
                        )}
                      >
                        {opt.icon}
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </SettingRow>
                <SettingRow
                  title="Reduced motion"
                  description="Follows your operating system accessibility setting automatically."
                  last
                >
                  <Badge variant="outline">System</Badge>
                </SettingRow>
              </Card>
            )}

            {/* Models */}
            {activeSection === 'models' && (
              <Card className="p-4 space-y-3">
                <SectionTitle>Models</SectionTitle>
                <div className="flex items-center justify-between py-2 border-b border-border">
                  <div>
                    <h3 className="text-sm font-medium text-primary">Installed models</h3>
                    <p className="text-xs text-secondary mt-0.5">
                      {intllm.models.filter((m) => m.installed).length} model(s) available via Ollama
                    </p>
                  </div>
                  <Button variant="outline" size="sm" onClick={() => intllm.refresh()}>
                    Refresh
                  </Button>
                </div>
                {intllm.models.length === 0 ? (
                  <p className="text-xs text-muted py-2">
                    {intllm.modelsError ?? 'No models detected. Pull a model in the Models workspace.'}
                  </p>
                ) : (
                  <div className="space-y-1.5">
                    {intllm.models.map((m) => (
                      <div
                        key={m.id}
                        className="flex items-center justify-between gap-3 px-3 py-2 rounded-md border border-border bg-canvas text-xs"
                      >
                        <span className="font-mono text-primary truncate">{m.name}</span>
                        <span className="flex items-center gap-2 text-muted font-mono shrink-0">
                          {m.parameterSize && <span>{m.parameterSize}</span>}
                          {m.installed ? (
                            <Badge variant="emerald" size="sm" dot>
                              Ready
                            </Badge>
                          ) : (
                            <Badge variant="outline" size="sm">
                              Not installed
                            </Badge>
                          )}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            )}

            {/* Ollama */}
            {activeSection === 'ollama' && (
              <Card className="p-4 space-y-3">
                <SectionTitle>Ollama</SectionTitle>
                <SettingRow
                  title="Daemon endpoint"
                  description="Managed by the INTLLM backend; change via backend configuration."
                  last
                >
                  <code className="text-xs font-mono text-secondary">{OLLAMA_DEFAULT_URL}</code>
                </SettingRow>
                {intllm.ollama && (
                  <div className="space-y-1.5 text-xs font-mono">
                    <div className="flex justify-between px-3 py-2 rounded-md bg-canvas border border-border">
                      <span className="text-secondary">Status</span>
                      <span className={intllm.ollama.status === 'running' ? 'text-success' : 'text-warning'}>
                        {intllm.ollama.status}
                      </span>
                    </div>
                    <div className="flex justify-between px-3 py-2 rounded-md bg-canvas border border-border">
                      <span className="text-secondary">Version</span>
                      <span className="text-primary">{intllm.ollama.version ?? '—'}</span>
                    </div>
                    <div className="flex justify-between px-3 py-2 rounded-md bg-canvas border border-border">
                      <span className="text-secondary">Models installed</span>
                      <span className="text-primary">{intllm.ollama.modelCount ?? '—'}</span>
                    </div>
                  </div>
                )}
              </Card>
            )}

            {/* Memory */}
            {activeSection === 'memory' && (
              <Card className="p-4">
                <SectionTitle>Memory</SectionTitle>
                <SettingRow
                  title="L0 Flash Brain micro-caching"
                  description="Sub-15ms vector routing before querying the L2 PostgreSQL store."
                >
                  <Switch checked={l0Caching} onChange={setL0Caching} />
                </SettingRow>
                <SettingRow
                  title="Background learning"
                  description="Low-priority memory maintenance; always yields to interactive requests."
                  last
                >
                  <Badge variant="outline">P3 · yields to chat</Badge>
                </SettingRow>
              </Card>
            )}

            {/* Internet */}
            {activeSection === 'internet' && (
              <Card className="p-4">
                <SectionTitle>Internet</SectionTitle>
                <SettingRow
                  title="Strict source verification"
                  description="Filter web search results with trust scores below 80%."
                >
                  <Switch checked={webVerification} onChange={setWebVerification} />
                </SettingRow>
                <SettingRow
                  title="Gateway status"
                  description="Live web retrieval availability reported by the runtime."
                  last
                >
                  <Badge variant={intllm.services?.web?.status === 'connected' ? 'emerald' : 'outline'} dot>
                    {intllm.services?.web?.status === 'connected' ? 'Connected' : 'Unavailable'}
                  </Badge>
                </SettingRow>
              </Card>
            )}

            {/* Browser */}
            {activeSection === 'browser' && (
              <Card className="p-4">
                <SectionTitle>Browser</SectionTitle>
                <SettingRow
                  title="Sandboxed browser agent"
                  description="Automation runs in an isolated Playwright context with per-action permissions."
                  last
                >
                  <Badge variant={intllm.services?.browser?.status === 'connected' ? 'emerald' : 'outline'} dot>
                    {intllm.services?.browser?.status === 'connected' ? 'Connected' : 'Unavailable'}
                  </Badge>
                </SettingRow>
              </Card>
            )}

            {/* Tools */}
            {activeSection === 'tools' && (
              <Card className="p-4">
                <SectionTitle>Tools</SectionTitle>
                <SettingRow
                  title="Permission gateway"
                  description="Each tool declares a risk level; high-risk actions require approval."
                  last
                >
                  <Badge variant="outline">Policy: require-approval</Badge>
                </SettingRow>
              </Card>
            )}

            {/* API */}
            {activeSection === 'api' && (
              <Card className="p-4 space-y-3">
                <SectionTitle>API</SectionTitle>
                <div className="flex items-center justify-between py-2 border-b border-border">
                  <div>
                    <h3 className="text-sm font-medium text-primary">Local API</h3>
                    <p className="text-xs text-secondary mt-0.5">
                      INTLLM's own OpenAI-compatible gateway. Keys are INTLLM keys, not Ollama.
                    </p>
                  </div>
                  <Badge variant={intllm.connected ? 'emerald' : 'outline'} dot>
                    {intllm.connected ? 'Running' : 'Offline'}
                  </Badge>
                </div>
                <SettingRow
                  title="Endpoint"
                  description="Point any OpenAI-compatible client at this base URL."
                >
                  <code className="text-xs font-mono text-secondary">{OPENAI_BASE ?? 'unavailable'}</code>
                </SettingRow>
                <SettingRow
                  title="Authentication"
                  description="Send the key as a Bearer token or x-api-key header."
                  last
                >
                  <code className="text-xs font-mono text-secondary">Authorization: Bearer sk-intllm-…</code>
                </SettingRow>
                <p className="text-[11px] text-muted">
                  Manage keys in the API workspace. Secrets are shown exactly once at creation;
                  only a hash is stored. Open the Docs page for full endpoint reference.
                </p>
              </Card>
            )}

            {/* Security */}
            {activeSection === 'security' && (
              <Card className="p-4 space-y-1">
                <SectionTitle>Security</SectionTitle>
                <SettingRow
                  title="Strict local storage only"
                  description="Prevents any external API connections except explicit live web searches."
                >
                  <Switch checked={localOnly} onChange={setLocalOnly} />
                </SettingRow>
                <SettingRow
                  title="Anonymous diagnostics"
                  description="Opt-in telemetry for hardware detection debugging. Off by default."
                  last
                >
                  <Switch checked={telemetry} onChange={setTelemetry} />
                </SettingRow>
                <div className="mt-3 flex items-start gap-2 p-3 rounded-md bg-success/5 border border-success/20">
                  <ShieldCheck className="w-4 h-4 text-success shrink-0 mt-0.5" aria-hidden />
                  <p className="text-xs text-secondary leading-relaxed">
                    Conversations, model weights, embeddings, and vector memory stay strictly on this device by
                    default. Nothing is transmitted to cloud services unless live web retrieval is explicitly enabled
                    for a message.
                  </p>
                </div>
              </Card>
            )}

            {/* Advanced */}
            {activeSection === 'advanced' && (
              <Card className="p-4 space-y-3">
                <SectionTitle>Advanced</SectionTitle>
                <div className="space-y-1.5 font-mono text-xs">
                  {runtimeRows.map((row) => (
                    <div
                      key={row.label}
                      className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 px-3 py-2 rounded-md bg-canvas border border-border"
                    >
                      <span className="text-secondary">{row.label}</span>
                      <span className="text-primary break-all">{row.value}</span>
                    </div>
                  ))}
                </div>
                <p className="text-[11px] text-muted">
                  Environment variables are the source of truth and are read at build/start time. Secrets are never
                  exposed here.
                </p>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
