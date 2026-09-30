import React, { useEffect, useRef, useState } from 'react';
import {
  ChevronDown,
  Cpu,
  SlidersHorizontal,
  Sun,
  Moon,
  Laptop,
  WifiOff,
  Activity,
  CircleDot
} from 'lucide-react';
import { useTheme } from '../../hooks/use-theme';
import { BrandLogo } from '../ui/BrandLogo';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { Model } from '../../types';
import { HealthSnapshot } from '../../lib/api/client';

export interface HeaderProps {
  currentModelId: string;
  onModelSelect: (modelId: string) => void;
  onOpenSettings: () => void;
  onOpenBackgroundLearning?: () => void;
  onOpenSystem?: () => void;
  isConnected?: boolean;
  models?: Model[];
  services?: HealthSnapshot['services'];
  status?: 'ok' | 'degraded' | 'offline';
  /** Real Ollama daemon state from GET /api/ollama/status. */
  ollamaStatus?: 'running' | 'stopped' | 'starting' | 'stopping' | 'unavailable' | 'error';
}

export const Header: React.FC<HeaderProps> = ({
  currentModelId,
  onModelSelect,
  onOpenSettings,
  onOpenBackgroundLearning,
  onOpenSystem,
  isConnected = false,
  models = [],
  services = {},
  status = 'offline',
  ollamaStatus
}) => {
  const { theme, setTheme } = useTheme();
  const [modelDropdownOpen, setModelDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setModelDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', onClickOutside);
    return () => document.removeEventListener('mousedown', onClickOutside);
  }, []);

  const toggleTheme = () => {
    if (theme === 'dark') setTheme('light');
    else if (theme === 'light') setTheme('system');
    else setTheme('dark');
  };

  const getThemeIcon = () => {
    if (theme === 'dark') return <Moon className="w-4 h-4 text-cyan-400" />;
    if (theme === 'light') return <Sun className="w-4 h-4 text-amber-500" />;
    return <Laptop className="w-4 h-4 text-slate-400" />;
  };

  const runtimeUp = isConnected;

  const ollamaUp = ollamaStatus === 'running' || (ollamaStatus === undefined && services?.ollama?.status === 'connected');
  const ollamaLabel =
    ollamaStatus === 'running'
      ? 'Running'
      : ollamaStatus === 'starting' || ollamaStatus === 'stopping'
        ? ollamaStatus === 'starting'
          ? 'Starting…'
          : 'Stopping…'
        : ollamaStatus === 'error'
          ? 'Error'
          : ollamaStatus === 'unavailable' || ollamaStatus === 'stopped'
            ? 'Stopped'
            : services?.ollama?.status === 'connected'
              ? 'Running'
              : 'Stopped';

  const connectionLabel =
    status === 'offline' ? 'Offline' : status === 'degraded' ? 'Degraded' : 'Connected';

  return (
    <header className="h-14 bg-white dark:bg-[#0D1117] border-b border-slate-200 dark:border-[#21262D] px-4 flex items-center justify-between shrink-0 select-none z-20 transition-colors">
      {/* Left: Model Selector & Connection Badge */}
      <div className="flex items-center gap-3 min-w-0">
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setModelDropdownOpen(!modelDropdownOpen)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-slate-100 dark:bg-[#161B22] border border-slate-300 dark:border-[#30363D] text-xs font-mono text-slate-800 dark:text-slate-200 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-cyan-500"
            aria-haspopup="listbox"
            aria-expanded={modelDropdownOpen}
          >
            <Cpu className="w-3.5 h-3.5 text-slate-400" />
            <span className="font-semibold text-slate-700 dark:text-slate-200 max-w-[140px] truncate">
              {runtimeUp ? currentModelId || 'Select model' : 'No models available'}
            </span>
            <Badge variant="outline" size="sm">
              {runtimeUp ? 'Ollama' : 'Disconnected'}
            </Badge>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400 ml-1" />
          </button>

          {modelDropdownOpen && (
            <div
              role="listbox"
              className="absolute top-full left-0 mt-1.5 w-72 bg-white dark:bg-[#0D1117] border border-slate-200 dark:border-[#30363D] rounded-md shadow-2xl z-50 p-2 text-xs font-mono"
            >
              {models.length === 0 ? (
                <div className="p-2 text-slate-500 dark:text-slate-400 space-y-1">
                  <div className="font-bold text-slate-800 dark:text-slate-200">
                    No models detected
                  </div>
                  <p className="text-[11px] font-sans">
                    Connect the INTLLM runtime and Ollama daemon to load installed models.
                  </p>
                </div>
              ) : (
                models.map((model) => (
                  <button
                    key={model.id}
                    role="option"
                    aria-selected={model.name === currentModelId}
                    onClick={() => {
                      onModelSelect(model.name);
                      setModelDropdownOpen(false);
                    }}
                    className={`w-full flex items-center justify-between px-2 py-1.5 rounded text-left hover:bg-slate-100 dark:hover:bg-[#161B22] ${
                      model.name === currentModelId ? 'text-cyan-600 dark:text-cyan-400' : 'text-slate-700 dark:text-slate-300'
                    }`}
                  >
                    <span className="truncate">{model.name}</span>
                    <span className="text-[10px] text-slate-500">
                      {model.parameterSize ?? model.family ?? ''}
                    </span>
                  </button>
                ))
              )}
            </div>
          )}
        </div>

        {/* Compact Global Runtime Indicator (real backend + Ollama state) */}
        <button
          onClick={onOpenSystem}
          disabled={!onOpenSystem}
          title="Open System monitor"
          className={`hidden md:flex items-center gap-3 px-2.5 py-1 rounded border text-[11px] font-mono transition-colors ${
            runtimeUp && ollamaUp
              ? 'bg-emerald-950/20 border-emerald-800/40 text-emerald-500 dark:text-emerald-400'
              : runtimeUp
                ? 'bg-amber-950/30 border-amber-800/40 text-amber-500 dark:text-amber-400'
                : 'bg-rose-950/30 border-rose-800/40 text-rose-500 dark:text-rose-400'
          } ${onOpenSystem ? 'hover:brightness-110 cursor-pointer' : 'cursor-default'}`}
          aria-label="Open system runtime monitor"
        >
          <span className="flex items-center gap-1">
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                runtimeUp ? 'bg-emerald-400' : status === 'degraded' ? 'bg-amber-400' : 'bg-rose-400'
              }`}
            />
            INTLLM {connectionLabel}
          </span>
          <span className="text-slate-500">·</span>
          <span className="flex items-center gap-1">
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                ollamaUp
                  ? 'bg-emerald-400'
                  : ollamaStatus === 'starting' || ollamaStatus === 'stopping'
                    ? 'bg-cyan-400 animate-pulse'
                    : 'bg-slate-400'
              }`}
            />
            Ollama {ollamaLabel}
          </span>
        </button>
      </div>

      {/* Right: Status Badges, Theme Switcher & Settings */}
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleTheme}
          title={`Current theme: ${theme} (Click to switch)`}
          aria-label="Toggle theme"
        >
          {getThemeIcon()}
        </Button>

        {/* Background Learning status */}
        <button
          onClick={onOpenBackgroundLearning}
          className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-mono border transition-all bg-slate-100 dark:bg-[#161B22] text-slate-600 dark:text-slate-400 border-slate-300 dark:border-[#21262D] hover:border-slate-500"
          title="Background Maintenance Engine status"
        >
          <Activity className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-[11px]">{runtimeUp ? 'Maintenance' : 'Worker Offline'}</span>
        </button>

        {/* Settings button */}
        <Button
          variant="ghost"
          size="icon"
          onClick={onOpenSettings}
          title="Application Settings"
          aria-label="Open settings"
        >
          <SlidersHorizontal className="w-4 h-4 text-slate-400" />
        </Button>
      </div>
    </header>
  );
};
