import React from 'react';
import { cn } from '../../lib/utils';

export type SystemStatusState = 'ready' | 'active' | 'idle' | 'offline';

export interface StatusDotProps {
  label: string;
  state: SystemStatusState;
  /** Extra right-aligned meta text, e.g. "12.4 GB". */
  meta?: string;
  className?: string;
}

const STATE_STYLES: Record<SystemStatusState, { dot: string; text: string; label: string }> = {
  ready: { dot: 'bg-success', text: 'text-success', label: 'Ready' },
  active: { dot: 'bg-accent', text: 'text-accent', label: 'Active' },
  idle: { dot: 'bg-muted', text: 'text-muted', label: 'Idle' },
  offline: { dot: 'bg-error', text: 'text-error', label: 'Offline' }
};

/** Compact `Label · state` status row used for system/service indicators. */
export const StatusDot: React.FC<StatusDotProps> = ({ label, state, meta, className }) => {
  const s = STATE_STYLES[state];
  return (
    <div className={cn('flex items-center justify-between gap-2 text-xs font-mono min-w-0', className)}>
      <span className="flex items-center gap-2 min-w-0">
        <span className={cn('w-1.5 h-1.5 rounded-full shrink-0', s.dot)} aria-hidden />
        <span className="text-secondary truncate">{label}</span>
      </span>
      <span className="flex items-center gap-2 shrink-0">
        {meta && <span className="text-muted text-[10px]">{meta}</span>}
        <span className={cn('text-[11px]', s.text)}>{s.label}</span>
      </span>
    </div>
  );
};
