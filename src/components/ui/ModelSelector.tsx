import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Check, ChevronDown, Cpu } from 'lucide-react';
import { cn } from '../../lib/utils';
import { Model } from '../../types';

export interface ModelSelectorProps {
  currentModelId: string;
  onModelSelect: (modelId: string) => void;
  models: Model[];
  /** Whether the runtime currently has usable models. */
  connected?: boolean;
  className?: string;
}

/**
 * Shared model selector dropdown. Shows the active model with a ready status
 * dot and lets the user switch between installed Ollama models.
 */
export const ModelSelector: React.FC<ModelSelectorProps> = ({
  currentModelId,
  onModelSelect,
  models,
  connected = false,
  className
}) => {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onPointerDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onPointerDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const select = useCallback(
    (name: string) => {
      onModelSelect(name);
      setOpen(false);
    },
    [onModelSelect]
  );

  const activeModel = models.find((m) => m.name === currentModelId);

  return (
    <div className={cn('relative', className)} ref={rootRef}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={cn(
          'flex items-center gap-2 h-8 px-2.5 rounded-md border border-border bg-surface text-xs transition-colors',
          'hover:bg-panel-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50',
          open && 'bg-panel-hover'
        )}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label="Select model"
      >
        <Cpu className="w-3.5 h-3.5 text-muted shrink-0" aria-hidden />
        <span className="font-medium text-primary max-w-[180px] truncate">
          {connected ? currentModelId || 'Select model' : 'No model'}
        </span>
        {connected && currentModelId && (
          <span className="flex items-center gap-1 text-[10px] font-mono text-success" title="Model ready">
            <span className="w-1.5 h-1.5 rounded-full bg-success" aria-hidden />
            Ready
          </span>
        )}
        <ChevronDown
          className={cn('w-3.5 h-3.5 text-muted transition-transform', open && 'rotate-180')}
          aria-hidden
        />
      </button>

      {open && (
        <div
          role="listbox"
          aria-label="Installed models"
          className="absolute top-full left-0 mt-1.5 w-80 max-w-[calc(100vw-2rem)] bg-elevated border border-border rounded-md shadow-lg z-50 p-1 animate-scale-in"
        >
          {models.length === 0 ? (
            <div className="p-3 space-y-1">
              <div className="text-xs font-medium text-primary">No models detected</div>
              <p className="text-[11px] text-secondary font-sans leading-relaxed">
                {connected
                  ? 'Pull a model in the Models workspace to get started.'
                  : 'Connect the INTLLM runtime and Ollama daemon to load installed models.'}
              </p>
            </div>
          ) : (
            models.map((model) => {
              const isActive = model.name === currentModelId;
              return (
                <button
                  key={model.id}
                  role="option"
                  aria-selected={isActive}
                  onClick={() => select(model.name)}
                  className={cn(
                    'w-full flex items-center justify-between gap-3 px-2 py-1.5 rounded text-left text-xs transition-colors',
                    'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring',
                    isActive ? 'bg-panel-hover text-primary' : 'text-secondary hover:bg-panel-hover hover:text-primary'
                  )}
                >
                  <span className="flex items-center gap-2 min-w-0">
                    <Check className={cn('w-3.5 h-3.5 shrink-0', isActive ? 'text-accent' : 'opacity-0')} aria-hidden />
                    <span className="truncate font-medium">{model.name}</span>
                  </span>
                  <span className="shrink-0 flex items-center gap-2 text-[10px] font-mono text-muted">
                    {model.parameterSize && <span>{model.parameterSize}</span>}
                    {model.contextWindow && <span className="hidden sm:inline">{model.contextWindow}</span>}
                    {model.installed && (
                      <span className="flex items-center gap-1 text-success">
                        <span className="w-1 h-1 rounded-full bg-success" aria-hidden />
                        Ready
                      </span>
                    )}
                  </span>
                </button>
              );
            })
          )}
          {activeModel && (
            <div className="mt-1 pt-1.5 border-t border-border px-2 py-1 text-[10px] font-mono text-muted flex items-center gap-2 flex-wrap">
              {activeModel.family && <span>{activeModel.family}</span>}
              {activeModel.quantization && <span>{activeModel.quantization}</span>}
              {activeModel.contextWindow && <span>ctx {activeModel.contextWindow}</span>}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
