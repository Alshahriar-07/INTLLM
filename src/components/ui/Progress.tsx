import React from 'react';
import { cn } from '../../lib/utils';

export interface ProgressProps {
  value: number; // 0 to 100
  color?: 'cyan' | 'emerald' | 'amber' | 'rose';
  className?: string;
  showPercent?: boolean;
}

export const Progress: React.FC<ProgressProps> = ({
  value,
  color = 'cyan',
  className,
  showPercent = false
}) => {
  const colorClasses = {
    cyan: 'bg-cyan-500',
    emerald: 'bg-emerald-500',
    amber: 'bg-amber-500',
    rose: 'bg-rose-500'
  };

  const clamped = Math.min(100, Math.max(0, value));

  return (
    <div className={cn('flex items-center gap-2 w-full', className)}>
      <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden border border-slate-700/50">
        <div
          className={cn('h-full transition-all duration-300 rounded-full', colorClasses[color])}
          style={{ width: `${clamped}%` }}
        />
      </div>
      {showPercent && (
        <span className="text-xs font-mono text-slate-400 w-10 text-right">{Math.round(clamped)}%</span>
      )}
    </div>
  );
};
