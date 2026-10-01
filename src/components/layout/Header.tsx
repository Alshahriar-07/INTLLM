import React from 'react';
import { Monitor, Moon, SlidersHorizontal, Sun } from 'lucide-react';
import { useTheme } from '../../hooks/use-theme';
import { Button } from '../ui/Button';
import { ModelSelector } from '../ui/ModelSelector';
import { StatusDot } from '../ui/StatusDot';
import { Model } from '../../types';

export interface HeaderProps {
  currentModelId: string;
  onModelSelect: (modelId: string) => void;
  onOpenSettings: () => void;
  onOpenBackgroundLearning?: () => void;
  onOpenSystem?: () => void;
  isConnected?: boolean;
  models?: Model[];
  status?: 'ok' | 'degraded' | 'offline';
  /** Real Ollama daemon state from GET /api/ollama/status. */
  ollamaStatus?: 'running' | 'stopped' | 'starting' | 'stopping' | 'unavailable' | 'error';
}

const THEME_ICON = {
  dark: <Moon className="w-4 h-4" aria-hidden />,
  light: <Sun className="w-4 h-4" aria-hidden />,
  system: <Monitor className="w-4 h-4" aria-hidden />
} as const;

export const Header: React.FC<HeaderProps> = ({
  currentModelId,
  onModelSelect,
  onOpenSettings,
  isConnected = false,
  models = [],
  status = 'offline',
  ollamaStatus
}) => {
  const { theme, setTheme } = useTheme();

  const toggleTheme = () => {
    if (theme === 'dark') setTheme('light');
    else if (theme === 'light') setTheme('system');
    else setTheme('dark');
  };

  const ollamaUp = ollamaStatus === 'running';
  const runtimeState = !isConnected ? 'offline' : status === 'degraded' ? 'idle' : 'ready';
  const ollamaState = ollamaUp ? 'ready' : ollamaStatus === 'starting' || ollamaStatus === 'stopping' ? 'active' : 'offline';

  return (
    <header className="h-14 bg-canvas border-b border-border px-4 flex items-center justify-between gap-3 shrink-0 select-none z-20">
      {/* Left: Model selector + runtime indicators */}
      <div className="flex items-center gap-3 min-w-0">
        <ModelSelector
          currentModelId={currentModelId}
          onModelSelect={onModelSelect}
          models={models}
          connected={isConnected}
        />
        <div className="hidden lg:flex items-center gap-3">
          <StatusDot label="INTLLM" state={runtimeState} />
          <StatusDot
            label="Ollama"
            state={ollamaState}
            meta={ollamaStatus === 'starting' ? 'starting…' : undefined}
          />
        </div>
      </div>

      {/* Right: theme + settings */}
      <div className="flex items-center gap-1.5 shrink-0">
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleTheme}
          title={`Theme: ${theme} (click to switch)`}
          aria-label={`Current theme: ${theme}. Click to switch.`}
        >
          {THEME_ICON[theme]}
        </Button>
        <Button variant="ghost" size="icon" onClick={onOpenSettings} title="Settings" aria-label="Open settings">
          <SlidersHorizontal className="w-4 h-4" />
        </Button>
      </div>
    </header>
  );
};
