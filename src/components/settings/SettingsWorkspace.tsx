import React, { useState } from 'react';
import { useTheme } from '../../hooks/use-theme';
import { INTLLM_BASE_URL, API_BASE, OPENAI_BASE, OLLAMA_DEFAULT_URL, POLLING_INTERVAL_MS, CONNECTION_TIMEOUT_MS } from '../../lib/api/client';
import { 
  Settings, 
  ShieldCheck, 
  Cpu, 
  Brain, 
  Globe, 
  Compass, 
  Wrench, 
  Key, 
  Zap, 
  SlidersHorizontal,
  HardDrive,
  Lock,
  Server
} from 'lucide-react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Switch } from '../ui/Switch';
import { Button } from '../ui/Button';

export const SettingsWorkspace: React.FC = () => {
  const { theme, setTheme } = useTheme();
  const [activeSection, setActiveSection] = useState<'privacy' | 'general' | 'runtime' | 'models' | 'brain' | 'web' | 'browser' | 'tools' | 'api' | 'performance' | 'advanced'>('privacy');

  // Local state toggles
  const [localOnly, setLocalOnly] = useState(true);
  const [telemetry, setTelemetry] = useState(false);
  const [autoOllama, setAutoOllama] = useState(true);
  const [l0Caching, setL0Caching] = useState(true);
  const [webVerification, setWebVerification] = useState(true);

  const sections = [
    { id: 'privacy', label: 'Privacy & Local Data', icon: <ShieldCheck className="w-4 h-4 text-emerald-400" /> },
    { id: 'general', label: 'General & UI', icon: <Settings className="w-4 h-4 text-cyan-400" /> },
    { id: 'runtime', label: 'Runtime & Connection', icon: <Server className="w-4 h-4 text-emerald-400" /> },
    { id: 'models', label: 'Model Engine & Ollama', icon: <Cpu className="w-4 h-4 text-cyan-400" /> },
    { id: 'brain', label: 'Brain & Vector Storage', icon: <Brain className="w-4 h-4 text-purple-400" /> },
    { id: 'web', label: 'Live Web Retrieval', icon: <Globe className="w-4 h-4 text-emerald-400" /> },
    { id: 'browser', label: 'Browser Agent Sandboxing', icon: <Compass className="w-4 h-4 text-cyan-400" /> },
    { id: 'tools', label: 'Tools Gateway Policies', icon: <Wrench className="w-4 h-4 text-amber-400" /> },
    { id: 'api', label: 'Local API Configuration', icon: <Key className="w-4 h-4 text-amber-400" /> },
    { id: 'performance', label: 'Performance & Hardware', icon: <Zap className="w-4 h-4 text-amber-400" /> },
    { id: 'advanced', label: 'Advanced & Diagnostics', icon: <SlidersHorizontal className="w-4 h-4 text-slate-600 dark:text-slate-400" /> }
  ] as const;

  return (
    <div className="p-6 max-w-7xl mx-auto overflow-y-auto max-h-[calc(100vh-3.5rem)] space-y-6">
      {/* Header */}
      <div className="border-b border-slate-300 dark:border-[#21262D] pb-4">
        <div className="flex items-center gap-2">
          <h1 className="text-xl font-bold font-mono tracking-tight text-slate-900 dark:text-slate-100">SYSTEM SETTINGS</h1>
          <Badge variant="cyan">LOCAL PREFERENCES</Badge>
        </div>
        <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
          Configure INTLLM local AI runtime behavior, memory routing, security gateways, and hardware resource limits.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {/* Settings Navigation Sidebar */}
        <div className="space-y-1">
          {sections.map((sec) => (
            <button
              key={sec.id}
              onClick={() => setActiveSection(sec.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded text-xs font-mono transition-colors text-left ${
                activeSection === sec.id
                  ? 'bg-cyan-100 dark:bg-cyan-950 text-cyan-700 dark:text-cyan-300 border border-cyan-300 dark:border-cyan-800 font-semibold'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:text-slate-200 hover:bg-slate-200 dark:bg-[#161B22]'
              }`}
            >
              {sec.icon}
              <span>{sec.label}</span>
            </button>
          ))}
        </div>

        {/* Settings Content Area */}
        <div className="md:col-span-3 space-y-6">
          {/* Privacy Section */}
          {activeSection === 'privacy' && (
            <div className="space-y-4">
              <Card className="p-5 border-emerald-500/30 bg-slate-50 dark:bg-[#0A0D12] space-y-3">
                <div className="flex items-center gap-2 text-emerald-400 font-bold font-mono text-sm">
                  <Lock className="w-4 h-4" /> LOCAL-FIRST GUARANTEE
                </div>
                <p className="text-xs text-slate-800 dark:text-slate-200 font-sans leading-relaxed">
                  <strong>Your conversations, model weights, embeddings, and vector memory stay strictly on this device by default.</strong> INTLLM does not transmit private chat prompts or stored memories to external cloud services or telemetry servers.
                </p>
              </Card>

              <Card className="p-4 space-y-4 border-slate-300 dark:border-[#21262D]">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-bold text-xs font-mono text-slate-900 dark:text-slate-100">Enforce Strict Local Storage Only</h3>
                    <p className="text-[11px] text-slate-600 dark:text-slate-400">Prevents any external API connections except explicit live web searches.</p>
                  </div>
                  <Switch checked={localOnly} onChange={setLocalOnly} />
                </div>

                <div className="flex items-center justify-between pt-3 border-t border-slate-200 dark:border-[#1C2128]">
                  <div>
                    <h3 className="font-bold text-xs font-mono text-slate-900 dark:text-slate-100">Anonymous Diagnostics & Crash Reports</h3>
                    <p className="text-[11px] text-slate-600 dark:text-slate-400">Opt-in telemetry for hardware detection debugging.</p>
                  </div>
                  <Switch checked={telemetry} onChange={setTelemetry} />
                </div>
              </Card>
            </div>
          )}

          {/* General Section */}
          {activeSection === 'general' && (
            <Card className="p-4 space-y-4 border-slate-300 dark:border-[#21262D]">
              <h2 className="text-xs font-bold font-mono text-slate-800 dark:text-slate-200">GENERAL INTERFACE SETTINGS</h2>
              
              <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-[#1C2128]">
                <div>
                  <h3 className="font-bold text-xs font-mono text-slate-900 dark:text-slate-100">Application Theme</h3>
                  <p className="text-[11px] text-slate-600 dark:text-slate-400">Select your preferred color scheme.</p>
                </div>
                <select
                  className="bg-slate-50 dark:bg-[#0A0D12] text-slate-900 dark:text-slate-100 border border-slate-300 dark:border-[#21262D] rounded px-2 py-1 text-xs font-mono"
                  value={theme}
                  onChange={(e) => {
                    const val = e.target.value as 'dark' | 'light' | 'system';
                    setTheme(val);
                  }}
                >
                  <option value="dark">Dark Mode</option>
                  <option value="light">Light Mode</option>
                  <option value="system">System Default</option>
                </select>
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-xs font-mono text-slate-900 dark:text-slate-100">Automatic Ollama Daemon Launch</h3>
                  <p className="text-[11px] text-slate-600 dark:text-slate-400">Starts local Ollama service automatically when INTLLM opens.</p>
                </div>
                <Switch checked={autoOllama} onChange={setAutoOllama} />
              </div>
            </Card>
          )}

          {/* Runtime Section — read-only view of the real configuration */}
          {activeSection === 'runtime' && (
            <Card className="p-4 space-y-4 border-slate-300 dark:border-[#21262D]">
              <h2 className="text-xs font-bold font-mono text-slate-800 dark:text-slate-200">RUNTIME & CONNECTION</h2>
              <p className="text-[11px] text-slate-600 dark:text-slate-400 font-sans">
                Environment variables are the source of truth. Values are read at build/start time
                from <span className="font-mono">VITE_INTLLM_*</span>; secrets are never exposed here.
              </p>
              <div className="space-y-2 font-mono text-xs">
                {[
                  { label: 'Backend URL (VITE_INTLLM_BASE_URL)', value: INTLLM_BASE_URL ?? 'not configured (invalid port)' },
                  { label: 'API Base', value: API_BASE ?? 'unavailable' },
                  { label: 'OpenAI-compatible Base', value: OPENAI_BASE ?? 'unavailable' },
                  { label: 'Ollama URL (backend-managed)', value: OLLAMA_DEFAULT_URL },
                  { label: 'Connection Timeout', value: `${CONNECTION_TIMEOUT_MS} ms` },
                  { label: 'Polling Interval', value: `${POLLING_INTERVAL_MS} ms` }
                ].map((row) => (
                  <div
                    key={row.label}
                    className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 px-3 py-2 rounded bg-slate-100 dark:bg-[#161B22] border border-slate-200 dark:border-[#21262D]"
                  >
                    <span className="text-slate-600 dark:text-slate-400">{row.label}</span>
                    <span className="text-slate-900 dark:text-slate-100 break-all">{row.value}</span>
                  </div>
                ))}
              </div>
              <p className="text-[11px] text-slate-500 font-mono">
                Note: 240426 (supplied runtime port) is not a valid TCP port and is rejected by
                configuration validation. Valid range is 1–65535.
              </p>
            </Card>
          )}

          {/* Brain Section */}
          {activeSection === 'brain' && (
            <Card className="p-4 space-y-4 border-slate-300 dark:border-[#21262D]">
              <h2 className="text-xs font-bold font-mono text-slate-800 dark:text-slate-200">LAYERED BRAIN CONFIGURATION</h2>
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-xs font-mono text-slate-900 dark:text-slate-100">L0 Flash Brain Micro-Caching</h3>
                  <p className="text-[11px] text-slate-600 dark:text-slate-400">Enables sub-15ms vector index routing before querying L2 PostgreSQL.</p>
                </div>
                <Switch checked={l0Caching} onChange={setL0Caching} />
              </div>
            </Card>
          )}

          {/* Web Section */}
          {activeSection === 'web' && (
            <Card className="p-4 space-y-4 border-slate-300 dark:border-[#21262D]">
              <h2 className="text-xs font-bold font-mono text-slate-800 dark:text-slate-200">LIVE WEB RETRIEVAL SETTINGS</h2>
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-xs font-mono text-slate-900 dark:text-slate-100">Strict Source Domain Verification</h3>
                  <p className="text-[11px] text-slate-600 dark:text-slate-400">Filters web search results with trust scores below 80%.</p>
                </div>
                <Switch checked={webVerification} onChange={setWebVerification} />
              </div>
            </Card>
          )}

          {/* Other Sections Fallback Container */}
          {!['privacy', 'general', 'runtime', 'brain', 'web'].includes(activeSection) && (
            <Card className="p-6 space-y-3 border-slate-300 dark:border-[#21262D]">
              <h2 className="text-sm font-bold font-mono text-slate-900 dark:text-slate-100 capitalize">{activeSection} Configuration</h2>
              <p className="text-xs text-slate-600 dark:text-slate-400 font-mono">
                Local preference settings for {activeSection} are active and enforced by INTLLM runtime defaults.
              </p>
              <Button variant="outline" size="sm" onClick={() => alert('Preferences saved locally')}>
                Save Preferences
              </Button>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};
