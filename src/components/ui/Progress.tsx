import React from 'react';
import { cn } from '../../lib/utils';

export interface ProgressProps {
  value: number; // 0 to 100
  color?: 'accent' | 'cyan' | 'success' | 'emerald' | 'warning' | 'amber' | 'error' | 'rose';
  className?: string;
  showPercent?: boolean;
}

export const Progress: React.FC<ProgressProps> = ({
  value,
  color = 'accent',
  className,
  showPercent = false
}) => {
  const colorClasses = {
    accent: 'bg-accent',
    cyan: 'bg-accent',
    success: 'bg-success',
    emerald: 'bg-success',
    warning: 'bg-warning',
    amber: 'bg-warning',
    error: 'bg-error',
    rose: 'bg-error'
  } as const;

  const clamped = Math.min(100, Math.max(0, value));

  return (
    <div className={cn('flex items-center gap-2 w-full', className)}>
      <div className="flex-1 h-1.5 bg-panel-hover rounded-full overflow-hidden">
        <div
          className={cn('h-full transition-[width] duration-300 rounded-full', colorClasses[color])}
          style={{ width: `${clamped}%` }}
        />
      </div>
      {showPercent && (
        <span className="text-xs font-mono text-muted w-10 text-right">{Math.round(clamped)}%</span>
      )}
    </div>
  );
};
